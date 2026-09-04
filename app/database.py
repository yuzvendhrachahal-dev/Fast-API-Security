import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")

client = AsyncMongoClient(MONGO_URL)
database = client["fastapi-security"]
user_collection = database["user"]
refresh_token_collection = database["refresh_tokens"]


async def init_db():
    await user_collection.create_index("email", unique=True)
