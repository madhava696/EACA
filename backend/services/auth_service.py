import bcrypt
import passlib.hash
import jwt
import os
from datetime import datetime, timedelta

JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"


# ---------------- PASSWORD & SECRET KEY HASHING ----------------

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def hash_secret_key(secret_key: str) -> str:
    """Hash secret key using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(secret_key.encode("utf-8"), salt).decode("utf-8")


def verify_secret_key(plain_key: str, hashed_key: str) -> bool:
    """Verify secret key using bcrypt."""
    try:
        return bcrypt.checkpw(plain_key.encode("utf-8"), hashed_key.encode("utf-8"))
    except Exception:
        return False


# ---------------- JWT TOKEN CREATION ----------------

def create_access_token(user_id: str) -> str:
    """Generate JWT token for a user."""
    expire = datetime.utcnow() + timedelta(days=1)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
