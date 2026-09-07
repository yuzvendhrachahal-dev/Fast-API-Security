import os

OTP_EXPIRE_MINUTES = int(
    os.getenv("OTP_EXPIRE_MINUTES", "5")
)

OTP_MAX_ATTEMPTS = int(
    os.getenv("OTP_MAX_ATTEMPTS", "5")
)

OTP_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60")
)