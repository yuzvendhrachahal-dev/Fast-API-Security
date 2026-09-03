import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient

load_dotenv()

MONGO_URL=os.getenv("MONGODB_URL")

client = AsyncMongoClient(MONGO_URL)
database = client["fastapi-security"]
user_collection = database["user"]