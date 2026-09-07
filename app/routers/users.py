from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.database import user_collection
from app.dependencies import get_current_user, require_admin
from app.schemas import UserCreate, UserPut, UserResponse, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


def user_to_response(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "is_verified": bool(user.get("is_email_verified", user.get("is_verified", False)))
    }


@router.get(
    "/me",
    response_model=UserResponse
)
async def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return user_to_response(current_user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_user(
    user: UserCreate,
    current_user: dict = Depends(require_admin)
):
    user_data = user.model_dump()
    user_data["role"] = "user"
    user_data["is_email_verified"] = False
    user_data["is_verified"] = False

    try:
        result = await user_collection.insert_one(user_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    user_data["_id"] = result.inserted_id
    return user_to_response(user_data)


@router.get(
    "/all",
    response_model=list[UserResponse]
)
async def get_all_users(
    current_user: dict = Depends(get_current_user)
):
    users_cursor = user_collection.find()
    users = await users_cursor.to_list(length=None)

    return [user_to_response(user) for user in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse
)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user_to_response(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse
)
async def replace_user(
    user_id: str,
    user: UserPut,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Only admin or the user themselves can update
    if current_user.get("role") != "admin" and str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    existing_user = await user_collection.find_one({"_id": ObjectId(user_id)})
    if existing_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": user.name, "email": user.email}}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    updated_user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return user_to_response(updated_user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse
)
async def update_user(
    user_id: str,
    user: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    update_data = user.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    # Role modification validation
    if "role" in update_data:
        # Require admin to change roles
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to change user roles"
            )

        if update_data["role"] not in ["admin", "user"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin' or 'user'"
            )

        # Admin self-protection: Cannot remove own admin role
        if str(current_user["_id"]) == user_id and update_data["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot remove their own admin privileges"
            )

    # Non-admin users cannot update other users
    if current_user.get("role") != "admin" and str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )

    try:
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    updated_user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return user_to_response(updated_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Admin self-protection: Cannot delete own account
    if str(current_user["_id"]) == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot delete their own account"
        )

    result = await user_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return None
