"""Application initialization and startup logic."""
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole


def initialize_defaults() -> None:
    """Initialize default data (e.g., admin user) on application startup."""
    db = SessionLocal()
    try:
        # Create default admin user if none exists
        existing_admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not existing_admin:
            admin = User(
                name="System Admin",
                email="admin@example.com",
                password=hash_password("Admin@12345"),
                role=UserRole.ADMIN,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
