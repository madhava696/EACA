# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response # ✅ Added Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.utils.database import get_db # Keep import for potential future use
from backend.models.user import User
from backend.services.auth_service import hash_password, verify_password, create_access_token, hash_secret_key
import logging # For logging

logger = logging.getLogger("backend.auth") # Get logger specific to this router

router = APIRouter(prefix="/api", tags=["auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str
    secret_key: str

# --- ✅ Explicit OPTIONS handler for /register ---
@router.options("/register")
async def options_register():
    logger.info("OPTIONS /register handled explicitly.") # Add logging
    return Response(status_code=status.HTTP_200_OK)
# -----------------------------------------------

@router.post("/register")
# --- ❌ Temporarily REMOVED DB dependency for debugging OPTIONS ---
# async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)):
async def register(payload: RegisterIn):
    logger.info(f"POST /register received for email: {payload.email}")
    # --- Dummy logic for debugging ---
    # This block is temporary. We are just checking if removing DB access
    # allows the OPTIONS request to pass. Do NOT use this in production.
    logger.warning("!!! Database interaction temporarily disabled for register endpoint debugging !!!")
    # Simulate success without DB interaction
    dummy_user_id = "temp-debug-user-id"
    # End dummy logic
    # --- Original DB logic commented out ---
    # q = await db.execute(select(User).filter_by(email=payload.email))
    # if q.scalars().first():
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    # user = User(
    #     email=payload.email,
    #     password_hash=hash_password(payload.password),
    #     secret_key_hash=hash_secret_key(payload.secret_key)
    # )
    # db.add(user)
    # await db.commit()
    # return {"message": "User registered successfully", "user_id": str(user.id)}
    # --- End original DB logic ---

    return {"message": "[DEBUG] Registration endpoint hit (DB skipped)", "user_id": dummy_user_id}

# --- ✅ Explicit OPTIONS handler for /login ---
@router.options("/login")
async def options_login():
    logger.info("OPTIONS /login handled explicitly.") # Add logging
    return Response(status_code=status.HTTP_200_OK)
# ---------------------------------------------

@router.post("/login")
# --- ❌ Temporarily REMOVED DB dependency for debugging OPTIONS ---
# async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)):
async def login(payload: LoginIn):
    logger.info(f"POST /login received for email: {payload.email}")
    # --- Dummy logic for debugging ---
    logger.warning("!!! Database interaction temporarily disabled for login endpoint debugging !!!")
    # Simulate a login failure for now without DB
    # In a real debug scenario, you might return a dummy token if needed
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="[DEBUG] Invalid credentials (DB skipped)")
    # --- Original DB logic commented out ---
    # q = await db.execute(select(User).filter_by(email=payload.email))
    # user = q.scalars().first()
    # if not user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # if not verify_password(payload.password, user.password_hash):
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # if user.secret_key_hash and user.secret_key_hash != hash_secret_key(payload.secret_key):
    #      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    # elif not user.secret_key_hash:
    #      pass # Or add specific validation if secret key is mandatory post-registration
    # token = create_access_token(user.id)
    # return {"message": "logged_in", "token": token}
    # --- End original DB logic ---

