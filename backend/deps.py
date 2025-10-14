# backend/deps.py
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from backend.utils.database import get_db
from backend.services.auth_service import decode_access_token
from backend.models.user import User
from sqlalchemy.future import select

async def get_current_user(authorization: str = Header(None), db: AsyncSession = Depends(get_db)):
    """
    Expect Authorization: Bearer <token>
    Returns User instance or raises 401.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user_id = payload["sub"]
    # fetch user
    q = await db.execute(select(User).filter_by(id=user_id))
    user = q.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user