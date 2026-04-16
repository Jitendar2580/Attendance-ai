from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    role: UserRole
    team_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    role: UserRole | None = None
    team_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
