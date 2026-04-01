import uuid
from curl_cffi.requests.session import BaseSession
from sqlalchemy import Column, String, Date, Boolean, DateTime, CheckConstraint, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from infrastructure.database import Base
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import relationship
from datetime import date
from typing import Literal




class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    investor_profile = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "investor_profile IN ('CONSERVATIVE', 'MODERATE', 'AGGRESSIVE')",
            name='users_investor_profile_check'
        ),
    )

class UserWatchlist(Base):
    __tablename__ = "user_watchlist"

    # id uuid DEFAULT uuid_generate_v4() NOT NULL
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # user_id uuid NOT NULL
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # tickers jsonb NOT NULL
    # Aqui é onde sua lista de objetos Asset (ticker, name, icon_url) será salva
    tickers = Column(JSONB, nullable=False, default=[])

    # added_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL
    added_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )

    # Relacionamento opcional para acessar o objeto User diretamente
    # user = relationship("User", back_populates="watchlist")

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    birth_date: date
    investor_profile: Literal['CONSERVATIVE', 'MODERATE', 'AGGRESSIVE']

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Como o usuário será retornado (sem a senha, por segurança!)
class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    birth_date: date
    investor_profile: str
    is_active: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    investor_profile: Literal['CONSERVATIVE', 'MODERATE', 'AGGRESSIVE']


