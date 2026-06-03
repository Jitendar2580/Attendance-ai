from passlib.context import CryptContext

# Argon2 is the recommended algorithm - handles passwords longer than 72 bytes safely
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# Maximum password length in bytes for bcrypt compatibility (72 bytes)
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Raised when password exceeds maximum allowed length."""
    pass


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2 algorithm.
    
    Args:
        password: Plain-text password to hash
        
    Returns:
        Hashed password string
        
    Raises:
        PasswordTooLongError: If password exceeds 72 bytes when encoded as UTF-8
    """
    # Encode to UTF-8 and check byte length
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            "Password exceeds maximum allowed length (72 bytes)."
        )
    
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a hashed password.
    
    Args:
        plain_password: Plain-text password to verify
        hashed_password: Hashed password to check against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)
