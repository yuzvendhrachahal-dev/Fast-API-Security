from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, status
from pymongo.errors import DuplicateKeyError

from app.database import refresh_token_collection, user_collection
from app.rate_limiter import limiter
from app.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(user: RegisterRequest):
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )

    password_hash = hash_password(user.password)

    user_document = {
        "name": user.name,
        "email": user.email,
        "password_hash": password_hash,
        "role": "user",
        "is_email_verified": False,
        "is_verified": False,
        "is_mobile_verified": False
    }

    try:
        result = await user_collection.insert_one(user_document)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists"
        )

    return {
        "id": str(result.inserted_id),
        "name": user.name,
        "email": user.email,
        "role": "user",
        "is_verified": False
    }


@router.post(
    "/login",
    response_model=TokenResponse
)
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginRequest):
    user = await user_collection.find_one({"email": credentials.email})

    if (
        user is None
        or "password_hash" not in user
        or not verify_password(credentials.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        user_id=str(user["_id"]),
        role=user.get("role", "user")
    )

    refresh_token = create_refresh_token()
    refresh_token_hash = hash_refresh_token(refresh_token)

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    await refresh_token_collection.insert_one({
        "user_id": str(user["_id"]),
        "token_hash": refresh_token_hash,
        "created_at": now,
        "expires_at": expires_at,
        "revoked": False
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }


@router.post("/refresh")
async def refresh_access_token(request: RefreshTokenRequest):
    token_hash = hash_refresh_token(request.refresh_token)

    stored_token = await refresh_token_collection.find_one({
        "token_hash": token_hash
    })

    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if stored_token["revoked"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revoked"
        )

    now = datetime.now(timezone.utc)

    # Check token expiration
    expires_at = stored_token["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    user = await user_collection.find_one(
        {"_id": ObjectId(stored_token["user_id"])}
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Revoke old refresh token
    await refresh_token_collection.update_one(
        {"_id": stored_token["_id"]},
        {"$set": {"revoked": True}}
    )

    # Create new refresh token
    new_refresh_token = create_refresh_token()
    new_refresh_token_hash = hash_refresh_token(new_refresh_token)
    new_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    await refresh_token_collection.insert_one({
        "user_id": str(user["_id"]),
        "token_hash": new_refresh_token_hash,
        "created_at": now,
        "expires_at": new_expires_at,
        "revoked": False
    })

    # Create new access token
    new_access_token = create_access_token(
        user_id=str(user["_id"]),
        role=user.get("role", "user")
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token
    }


@router.post("/logout")
async def logout(request: RefreshTokenRequest):
    token_hash = hash_refresh_token(request.refresh_token)

    result = await refresh_token_collection.update_one(
        {
            "token_hash": token_hash,
            "revoked": False
        },
        {
            "$set": {
                "revoked": True
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    return {
        "message": "Logged out successfully"
    }
