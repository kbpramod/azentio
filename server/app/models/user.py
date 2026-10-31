from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from app.db.session import Base


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    hashed_refresh_token = Column(String(255), nullable=True)  # Store active refresh token hash
    role = Column(String(50), default="customer", nullable=False)  # customer, agent, admin
    account_number = Column(String(50), unique=True, index=True, nullable=False)
    balance = Column(Float, default=2500.0, nullable=False)
    ai_credits = Column(Integer, default=500, nullable=False)  # AI Credits for banking queries
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
