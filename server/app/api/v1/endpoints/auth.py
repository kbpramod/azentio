import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.auth import (
    CustomerRegisterRequest,
    LoginRequest,
    LogoutResponse,
    TokenResponse,
    UserOut,
)

router = APIRouter()


def _generate_account_number() -> str:
    return f"AZ-{random.randint(100000, 999999)}"


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new banking customer",
)
async def register_customer(
    payload: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer with this email address already exists.",
        )

    # Create customer account
    account_number = _generate_account_number()
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="customer",
        account_number=account_number,
        balance=payload.initial_deposit,
        ai_credits=500,  # Starting AI credits for customer agent
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # Initial opening deposit transaction record
    if payload.initial_deposit > 0:
        initial_tx = Transaction(
            user_id=new_user.id,
            type="deposit",
            amount=payload.initial_deposit,
            description="Account Opening Initial Deposit",
            status="completed",
        )
        db.add(initial_tx)

    await db.commit()
    await db.refresh(new_user)

    # Generate JWT access token
    access_token = create_access_token(
        subject=new_user.email,
        extra_claims={
            "user_id": new_user.id,
            "role": new_user.role,
            "account_number": new_user.account_number,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserOut.model_validate(new_user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Customer Login",
)
async def login_customer(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your bank account is currently deactivated. Please contact support.",
        )

    access_token = create_access_token(
        subject=user.email,
        extra_claims={
            "user_id": user.id,
            "role": user.role,
            "account_number": user.account_number,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserOut.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Customer Logout",
)
async def logout_customer() -> LogoutResponse:
    """Clear client session and acknowledge customer logout."""
    return LogoutResponse(message="Customer logged out successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current authenticated customer",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Retrieve full customer profile, account details, balance, and AI credits."""
    return UserOut.model_validate(current_user)

