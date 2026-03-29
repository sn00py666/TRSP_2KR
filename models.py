from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int | None = Field(default=None, ge=0)
    is_subscribed: bool | None = None

