# backend/routers/profile.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from backend.deps import get_current_user
from backend.utils.database import get_db
from backend.models.user import User
from backend.services.auth_service import hash_password, hash_secret_key
from sqlalchemy.future import select

router = APIRouter(prefix="/api", tags=["profile"])

class UpdateProfile(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    secret_key: str | None = None

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    # Return safe user info (no hashes)
    return {"id": str(current_user.id), "email": current_user.email, "created_at": current_user.created_at}

@router.patch("/me")
async def update_profile(payload: UpdateProfile, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated = False
    if payload.email:
        current_user.email = payload.email
        updated = True
    if payload.password:
        current_user.password_hash = hash_password(payload.password)
        updated = True
    if payload.secret_key:
        current_user.secret_key_hash = hash_secret_key(payload.secret_key)
        updated = True
    if updated:
        db.add(current_user)
        await db.commit()
    return {"message": "updated"}

@router.delete("/me/emotion-data")
async def delete_emotion_hook(current_user: User = Depends(get_current_user)):
    # Server does not keep emotion data; this endpoint exists for frontend to call if needed.
    # We simply acknowledge.
    return {"message": "server-side hooks cleared (no emotion stored server-side)"}
