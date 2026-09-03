from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.database import client, user_collection
from app.schemas import UserCreate, UserResponse, UserUpdate, UserPut
from bson import ObjectId
from typing import List

app = FastAPI()


@app.get("/")
async def home():
    return {
        "message": "FastAPI is running",
        "name ":"Nivash"
    }

@app.get("/health")
async def health():
    await client.admin.command("ping")
    return {
        "message" : "DB is connected"
    }

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

@app.post(
    "/users", 
    response_model=UserResponse,
    status_code=201
)
async def create_user(user: UserCreate):
    
    user_data = user.model_dump()
    
    await user_collection.create_index("email", unique=True)
    
    try:
        result = await user_collection.insert_one(user_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    created_user = await user_collection.find_one(
        {"_id": result.inserted_id}
    )
    
    return {
        "id": str(created_user["_id"]),
        "name": created_user["name"],
        "email": created_user["email"],
        "age": created_user["age"]
    }


@app.get(
    "/users/all",
    response_model=List[UserResponse]
)
async def get_all_users():
    
    users_cursor = user_collection.find()
    
    users = await users_cursor.to_list(length=None)
    
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No users found"
        )
    
    return [
        {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "age": user["age"]
        }
        for user in users
    ]

@app.get(
    "/users/{user_id}",
    response_model=UserResponse
)
async def get_user(user_id: str):

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user = await user_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "age": user["age"]
    }

@app.put(
    "/users/{user_id}",
    response_model=UserResponse
)
async def replace_user(
    user_id: str,
    user: UserPut
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID"
        )

    result = await user_collection.replace_one(
        {"_id": ObjectId(user_id)},
        {
            "name": user.name,
            "email": user.email,
            "age": user.age
        }
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    updated_user = await user_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    return {
        "id": str(updated_user["_id"]),
        "name": updated_user["name"],
        "email": updated_user["email"],
        "age": updated_user["age"]
    }


@app.patch(
    "/users/{user_id}",
    response_model=UserResponse
)
async def update_user(
    user_id: str,
    user: UserUpdate
):

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    update_data = user.model_dump(
        exclude_none=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    result = await user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updated_user = await user_collection.find_one(
        {"_id": ObjectId(user_id)}
    )

    return {
        "id": str(updated_user["_id"]),
        "name": updated_user["name"],
        "email": updated_user["email"],
        "age": updated_user["age"]
    }

@app.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(user_id: str):

    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    result = await user_collection.delete_one(
        {"_id": ObjectId(user_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return None