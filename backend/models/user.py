# backend/models/user.py
import sqlalchemy as sa
import uuid
from sqlalchemy.dialects.postgresql import UUID
from backend.utils.database import Base

class User(Base):
    __tablename__ = "users"
    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = sa.Column(sa.String(255), unique=True, nullable=False, index=True)
    password_hash = sa.Column(sa.String(512), nullable=False)
    # secret_key_hash is a SHA256 hex digest of the user's secret_key (server doesn't store plaintext)
    secret_key_hash = sa.Column(sa.String(128), nullable=True)
    created_at = sa.Column(sa.DateTime(timezone=True), server_default=sa.func.now())