import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL")


def send_otp_email(recipient_email: str, otp: str):

    print("OTP recipient:", recipient_email)

    message = EmailMessage()

    message["Subject"] = "Your Verification OTP"
    message["From"] = FROM_EMAIL
    message["To"] = recipient_email

    message.set_content(
        f"""
Hello,

Your verification OTP is:

{otp}

This OTP will expire in 5 minutes.

If you did not request this code, please ignore this email.
"""
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)