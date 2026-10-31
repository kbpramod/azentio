from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class CustomerRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Customer email address")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")
    full_name: str = Field(..., min_length=2, max_length=100, description="Customer full name")
    initial_deposit: float = Field(default=1000.0, ge=0, description="Initial opening deposit")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered customer email")
    password: str = Field(..., min_length=1, description="Account password")


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    account_number: str
    balance: float
    ai_credits: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    message: str = "Authentication successful"
    user: UserOut
    access_token: Optional[str] = None
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class TransactionOut(BaseModel):
    id: int
    user_id: int
    type: str
    amount: float
    description: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    recipient_account: str = Field(..., description="Target bank account number")
    amount: float = Field(..., gt=0, description="Transfer amount must be greater than zero")
    note: Optional[str] = Field("Online transfer", max_length=100)


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, description="Query for banking customer agent")


class AgentChatResponse(BaseModel):
    reply: str
    ai_credits_used: int
    remaining_credits: int
    timestamp: datetime
