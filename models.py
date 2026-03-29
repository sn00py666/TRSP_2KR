import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    age: int | None = Field(default=None, ge=0)
    is_subscribed: bool | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class CommonHeaders(BaseModel):
    user_agent: str
    accept_language: str

    @field_validator("accept_language")
    @classmethod
    def validate_accept_language(cls, value: str) -> str:
        pattern = r"^[A-Za-z]{2,3}(?:-[A-Za-z]{2})?(?:,\s*[A-Za-z]{2,3}(?:-[A-Za-z]{2})?(?:;q=(?:0(?:\.\d{1,3})?|1(?:\.0{1,3})?))?)*$"
        if re.fullmatch(pattern, value) is None:
            raise ValueError("Invalid Accept-Language format")
        return value

