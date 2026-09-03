from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=50
    )

    email: EmailStr

    age: int = Field(
        ge=1,
        le=120
    )


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    #age: int
    role: str

class UserUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=50
    )

    email: EmailStr | None = None

    age: int | None = Field(
        default=None,
        ge=1,
        le=120
    )

class UserPut(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=50
    )

    email: EmailStr

    age: int = Field(
        ge=1,
        le=120
    )

class RegisterRequest(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=50
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )


class LoginRequest(BaseModel):

    email: EmailStr

    password: str
