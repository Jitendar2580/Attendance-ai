from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def list_users(db: Session, offset: int = 0, limit: int = 20) -> list[User]:
    return list(db.scalars(select(User).offset(offset).limit(limit)))


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        email=payload.email,
        password=hash_password(payload.password),
        role=payload.role,
        team_id=payload.team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    update_data = payload.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        update_data["password"] = hash_password(update_data["password"])
    else:
        # Don't update password if None or empty
        update_data.pop("password", None)
    for key, value in update_data.items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
