from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter, HTTPException, Request, status

from app.database import otp_collection, user_collection
from app.rate_limiter import limiter
from app.schemas import SendOTPRequest, VerifyOTPRequest
from app.services.otp_service import generate_otp, hash_otp
from app.services.email_service import send_otp_email

router = APIRouter(
    prefix="/otp",
    tags=["OTP"]
)


OTP_EXPIRE_MINUTES = int(
    os.getenv("OTP_EXPIRE_MINUTES", "5")
)

OTP_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60")
)

OTP_MAX_ATTEMPTS = int(
    os.getenv("OTP_MAX_ATTEMPTS", "5")
)

OTP_MAX_RESENDS = int(
    os.getenv("OTP_MAX_RESENDS", "5")
)

OTP_RESEND_WINDOW_MINUTES = int(
    os.getenv("OTP_RESEND_WINDOW_MINUTES", "15")
)
# --------------------------------------------------
# SEND OTP
# --------------------------------------------------

@router.post("/send")
@limiter.limit("5/minute")
async def send_otp(request: Request, otp_request: SendOTPRequest):

    email = otp_request.email
    now = datetime.now(timezone.utc)

    existing_otp = await otp_collection.find_one(
        {"email": email}
    )

    resend_count = 0
    resend_window_start = now

    # -----------------------------------------
    # Existing OTP
    # -----------------------------------------

    if existing_otp:

        last_sent_at = existing_otp.get("last_sent_at")

        if last_sent_at:

            if last_sent_at.tzinfo is None:
                last_sent_at = last_sent_at.replace(
                    tzinfo=timezone.utc
                )

            cooldown_end = (
                last_sent_at
                + timedelta(
                    seconds=OTP_RESEND_COOLDOWN_SECONDS
                )
            )

            if now < cooldown_end:

                remaining = int(
                    (
                        cooldown_end - now
                    ).total_seconds()
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Please wait {remaining} seconds "
                        "before requesting another OTP"
                    )
                )

        # -----------------------------------------
        # Resend window
        # -----------------------------------------

        resend_window_start = existing_otp.get(
            "resend_window_start",
            now
        )

        if resend_window_start.tzinfo is None:
            resend_window_start = resend_window_start.replace(
                tzinfo=timezone.utc
            )

        resend_window_end = (
            resend_window_start
            + timedelta(
                minutes=OTP_RESEND_WINDOW_MINUTES
            )
        )

        if now < resend_window_end:

            resend_count = existing_otp.get(
                "resend_count",
                1
            )

            if resend_count >= OTP_MAX_RESENDS:

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Too many OTP requests. "
                        "Please try again later."
                    )
                )

        else:

            # Resend window expired.
            # Start a new window.
            resend_count = 0
            resend_window_start = now

    # -----------------------------------------
    # Generate new OTP
    # -----------------------------------------

    otp = generate_otp()

    otp_hash = hash_otp(otp)

    expires_at = (
        now
        + timedelta(
            minutes=OTP_EXPIRE_MINUTES
        )
    )

    # -----------------------------------------
    # OTP document
    # -----------------------------------------

    otp_document = {
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": expires_at,
        "attempts": 0,
        "created_at": now,
        "last_sent_at": now,

        # Preserve resend tracking
        "resend_count": resend_count + 1,
        "resend_window_start": resend_window_start
    }

    # -----------------------------------------
    # Store OTP
    # -----------------------------------------

    await otp_collection.update_one(
        {"email": email},
        {"$set": otp_document},
        upsert=True
    )

    # -----------------------------------------
    # Send email
    # -----------------------------------------

    try:

        print("OTP recipient:", email)

        send_otp_email(
            recipient_email=email,
            otp=otp
        )

    except Exception as e:

        print("EMAIL ERROR:", repr(e))

        await otp_collection.delete_one(
            {"email": email}
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )

    return {
        "message": "OTP sent successfully"
    }

# --------------------------------------------------
# VERIFY OTP
# --------------------------------------------------

@router.post("/verify")
async def verify_otp(request: VerifyOTPRequest):

    email = request.email
    otp = request.otp

    now = datetime.now(timezone.utc)

    # -----------------------------------------
    # Find OTP
    # -----------------------------------------

    otp_doc = await otp_collection.find_one(
        {"email": email}
    )

    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not found or expired"
        )

    # -----------------------------------------
    # Check expiration
    # -----------------------------------------

    expires_at = otp_doc.get("expires_at")

    if expires_at:

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        if now >= expires_at:

            await otp_collection.delete_one(
                {"_id": otp_doc["_id"]}
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired"
            )

    # -----------------------------------------
    # Check current attempts
    # -----------------------------------------

    attempts = otp_doc.get(
        "attempts",
        0
    )

    if attempts >= OTP_MAX_ATTEMPTS:

        await otp_collection.delete_one(
            {"_id": otp_doc["_id"]}
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed attempts. "
                "Please request a new OTP"
            )
        )

    # -----------------------------------------
    # Hash submitted OTP
    # -----------------------------------------

    submitted_otp_hash = hash_otp(otp)

    # -----------------------------------------
    # Correct OTP
    # -----------------------------------------

    if submitted_otp_hash == otp_doc.get("otp_hash"):

        result = await user_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "is_email_verified": True,
                    "is_verified": True
                }
            }
        )

        if result.matched_count == 0:

            await otp_collection.delete_one(
                {"_id": otp_doc["_id"]}
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Delete OTP immediately after success
        await otp_collection.delete_one(
            {"_id": otp_doc["_id"]}
        )

        return {
            "message": "OTP verified successfully"
        }

    # -----------------------------------------
    # Wrong OTP
    # -----------------------------------------

    result = await otp_collection.update_one(
        {
            "_id": otp_doc["_id"],
            "attempts": {
                "$lt": OTP_MAX_ATTEMPTS
            }
        },
        {
            "$inc": {
                "attempts": 1
            }
        }
    )

    # -----------------------------------------
    # Attempt limit reached during concurrent
    # requests
    # -----------------------------------------

    if result.modified_count == 0:

        await otp_collection.delete_one(
            {"_id": otp_doc["_id"]}
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many failed attempts. "
                "Please request a new OTP"
            )
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP"
    )

    