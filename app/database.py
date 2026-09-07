import os

from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

MONGO_URL = os.getenv(
    "MONGODB_URL",
    "mongodb://localhost:27017/"
)

client = AsyncMongoClient(MONGO_URL)

database = client["fastapi-security"]

user_collection = database["user"]

refresh_token_collection = database["refresh_tokens"]

otp_collection = database["otp_codes"]


async def create_indexes():

    # Unique email for users
    await user_collection.create_index(
        "email",
        unique=True
    )

    # Automatically delete expired OTPs
    await otp_collection.create_index(
        "expires_at",
        expireAfterSeconds=0
    )

    # Automatically delete expired refresh tokens
    await refresh_token_collection.create_index(
        "expires_at",
        expireAfterSeconds=0
    )


async def seed_admin():
    from app.security import hash_password

    admin = await user_collection.find_one({"email": "admin@admin.com"})
    if not admin:
        admin_doc = {
            "name": "Admin",
            "email": "admin@admin.com",
            "password_hash": hash_password("Admin@123"),
            "role": "admin",
            "is_verified": True,
            "is_email_verified": True,
            "is_mobile_verified": False,
        }
        await user_collection.insert_one(admin_doc)
        print("Default admin account created: admin@admin.com")
    else:
        # Ensure role is admin and verified
        updates = {}
        if admin.get("role") != "admin":
            updates["role"] = "admin"
        if not admin.get("is_verified") or not admin.get("is_email_verified"):
            updates["is_verified"] = True
            updates["is_email_verified"] = True
        if updates:
            await user_collection.update_one(
                {"email": "admin@admin.com"},
                {"$set": updates}
            )
        print("Admin account verified: admin@admin.com")