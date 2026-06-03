from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: UserRole
    team_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        """Ensure password does not exceed 72 bytes when UTF-8 encoded."""
        password_bytes = v.encode("utf-8")
        if len(password_bytes) > 72:
            raise ValueError("Password exceeds maximum allowed length (72 bytes).")
        return v


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    role: UserRole | None = None
    team_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str | None) -> str | None:
        """Ensure password does not exceed 72 bytes when UTF-8 encoded."""
        if v is not None:
            password_bytes = v.encode("utf-8")
            if len(password_bytes) > 72:
                raise ValueError("Password exceeds maximum allowed length (72 bytes).")
        return v


class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
