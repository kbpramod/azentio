import random
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    hash_token,
    set_auth_cookies,
    verify_password,
)
from app.db.session import get_db
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    CustomerRegisterRequest,
    LoginRequest,
    LogoutResponse,
    UserOut,
)

router = APIRouter()


def _generate_account_number() -> str:
    return f"AZ-{random.randint(100000, 999999)}"


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register customer with HttpOnly cookie tokens",
)
async def register_customer(
    payload: CustomerRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A customer with this email address already exists.",
        )

    account_number = _generate_account_number()
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role="customer",
        account_number=account_number,
        balance=payload.initial_deposit,
        ai_credits=500,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    if payload.initial_deposit > 0:
        initial_tx = Transaction(
            user_id=new_user.id,
            type="deposit",
            amount=payload.initial_deposit,
            description="Account Opening Initial Deposit",
            status="completed",
        )
        db.add(initial_tx)

    # Generate Access and Refresh Tokens
    access_token = create_access_token(
        subject=new_user.email,
        extra_claims={
            "user_id": new_user.id,
            "role": new_user.role,
            "account_number": new_user.account_number,
        },
    )
    refresh_token = create_refresh_token(subject=new_user.email)

    # Store refresh token hash in DB
    new_user.hashed_refresh_token = hash_token(refresh_token)
    await db.commit()
    await db.refresh(new_user)

    # Set HttpOnly Cookies
    set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)

    return AuthResponse(
        message="Registration successful",
        user=UserOut.model_validate(new_user),
        access_token=access_token,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Customer Login (sets HttpOnly Access & Refresh cookies)",
)
async def login_customer(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
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

    # Issue fresh Access and Refresh tokens
    access_token = create_access_token(
        subject=user.email,
        extra_claims={
            "user_id": user.id,
            "role": user.role,
            "account_number": user.account_number,
        },
    )
    refresh_token = create_refresh_token(subject=user.email)

    # Save refresh token hash in DB
    user.hashed_refresh_token = hash_token(refresh_token)
    await db.commit()
    await db.refresh(user)

    # Set secure HttpOnly cookies
    set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)

    return AuthResponse(
        message="Login successful",
        user=UserOut.model_validate(user),
        access_token=access_token,
    )


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Refresh Access Token using HttpOnly Refresh Cookie",
)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    # 1. Read refresh token from HttpOnly cookie
    refresh_token = request.cookies.get(settings.COOKIE_REFRESH_NAME)
    if not refresh_token:
        # Fallback to header or body if needed
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            refresh_token = auth_header.split(" ")[1]

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing. Please log in again.",
        )

    # 2. Decode and validate refresh token JWT
    payload = decode_token(refresh_token, expected_type="refresh")
    email: Optional[str] = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload.",
        )

    # 3. Lookup user and verify refresh token against database hash
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    # Validate token hash (ensures revoked tokens cannot be reused)
    if user.hashed_refresh_token != hash_token(refresh_token):
        # Possible token reuse/theft - revoke immediately
        user.hashed_refresh_token = None
        await db.commit()
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or expired.",
        )

    # 4. Issue a new access token (and rotate refresh token)
    new_access_token = create_access_token(
        subject=user.email,
        extra_claims={
            "user_id": user.id,
            "role": user.role,
            "account_number": user.account_number,
        },
    )
    new_refresh_token = create_refresh_token(subject=user.email)

    # Update hash in DB
    user.hashed_refresh_token = hash_token(new_refresh_token)
    await db.commit()
    await db.refresh(user)

    # Update cookies
    set_auth_cookies(response, access_token=new_access_token, refresh_token=new_refresh_token)

    return AuthResponse(
        message="Token refreshed successfully",
        user=UserOut.model_validate(user),
        access_token=new_access_token,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Customer Logout (clears HttpOnly cookies and invalidates refresh token)",
)
async def logout_customer(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    # Clear refresh token in DB if authenticated
    try:
        user = await get_current_user(request=request, credentials=None, db=db)
        if user:
            user.hashed_refresh_token = None
            await db.commit()
    except Exception:
        pass

    # Clear HttpOnly cookies in browser
    clear_auth_cookies(response)

    return LogoutResponse(message="Customer logged out successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current customer profile",
)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
