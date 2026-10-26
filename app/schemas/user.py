
from pydantic import BaseModel, EmailStr, Field, SecretStr


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: SecretStr = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool

    model_config = {"from_attributes": True}
