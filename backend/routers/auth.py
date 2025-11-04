from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.utils.database import get_db
from backend.models.user import User
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    hash_secret_key,
    verify_secret_key,
)
import logging
import re
from backend.deps import get_current_user

# ✅ DEFINE ROUTER HERE
router = APIRouter(prefix="/api/auth", tags=["auth"])

logger = logging.getLogger("backend.auth")


# ---------------------- MODELS ----------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str


# ---------------------- HELPERS ----------------------
def validate_password_strength(password: str):
    """Ensure password meets security requirements."""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="Password must include an uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="Password must include a lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must include a number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=400, detail="Password must include a special character.")


# ---------------------- ROUTES ----------------------
@router.options("/register")
async def options_register():
    logger.info("OPTIONS /register handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)


@router.post("/register")
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    logger.info(f"POST /register received for email: {payload.email}")
    print("🔍 Received payload:", payload.dict())

    # Optional password validation (can comment out for testing)
    # validate_password_strength(payload.password)

    # Check existing email
    existing = await db.execute(select(User).filter_by(email=payload.email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    secret_key_value = payload.secret_key or "default_secret"

    # Create new user
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        secret_key_hash=hash_secret_key(secret_key_value),
    )

    db.add(user)
    await db.commit()

    token = create_access_token(user.id)
    logger.info(f"✅ User registered successfully: {payload.email}")

    return {
        "message": "Registration successful.",
        "user": {"email": payload.email},
        "token": token,
    }


@router.options("/login")
async def options_login():
    logger.info("OPTIONS /login handled explicitly.")
    return Response(status_code=status.HTTP_200_OK)


@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    logger.info(f"POST /login received for email: {payload.email}")

    # Check if user exists
    q = await db.execute(select(User).filter_by(email=payload.email))
    user = q.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Verify password
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    # Verify secret key
    if not verify_secret_key(payload.secret_key, user.secret_key_hash):
        raise HTTPException(status_code=401, detail="Invalid secret key.")

    token = create_access_token(user.id)
    logger.info(f"✅ User logged in successfully: {payload.email}")

    return {
        "message": "Login successful.",
        "user": {"email": payload.email},
        "token": token,
    }


# ✅ /me route for current user info
@router.get("/me")
async def get_current_user_info(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": str(current_user.created_at),
    }
