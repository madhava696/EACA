# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.utils.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, verify_password, create_access_token, hash_secret_key

router = APIRouter(prefix="/api", tags=["auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str

@router.post("/register")
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
    # check if email exists
    q = await db.execute(select(User).filter_by(email=payload.email))
    if q.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        secret_key_hash=hash_secret_key(payload.secret_key)
    )
    db.add(user)
    await db.commit()
    token = create_access_token(user.id)
    return {"message": "registered", "token": token}

@router.post("/login")
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(User).filter_by(email=payload.email))
    user = q.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.secret_key_hash != hash_secret_key(payload.secret_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id)
    return {"message": "logged_in", "token": token}
