from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str = "user"
    is_verified: bool = False


class UserUpdate(BaseModel):  # PATCH
    name: str | None = Field(default=None, min_length=2, max_length=50)
    email: EmailStr | None = None
    role: str | None = None



class UserPut(BaseModel):  # PUT
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SendOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(
        min_length=6,
        max_length=6
    )