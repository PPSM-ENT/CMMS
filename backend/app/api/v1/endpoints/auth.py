"""
Authentication endpoints.
"""
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DBSession, CurrentUser, get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
)
from app.models.user import User, APIKey
from app.schemas.auth import (
    Token,
    LoginRequest,
    RefreshTokenRequest,
    PasswordChange,
    APIKeyCreate,
    APIKeyResponse,
)
from app.schemas.user import UserResponse
from app.schemas.common import MessageResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    db: DBSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.locked_until}",
        )

    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create tokens with organization context
    additional_claims = {"org_id": user.organization_id}

    return Token(
        access_token=create_access_token(user.id, additional_claims=additional_claims),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    db: DBSession,
    login_data: LoginRequest,
) -> Any:
    """
    JSON-based login endpoint.
    """
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.locked_until}",
        )

    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    await db.commit()

    additional_claims = {"org_id": user.organization_id}

    return Token(
        access_token=create_access_token(user.id, additional_claims=additional_claims),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    db: DBSession,
    token_data: RefreshTokenRequest,
) -> Any:
    """
    Refresh access token using refresh token.
    """
    payload = decode_token(token_data.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    additional_claims = {"org_id": user.organization_id}

    return Token(
        access_token=create_access_token(user.id, additional_claims=additional_claims),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    db: DBSession,
    current_user: CurrentUser,
    password_data: PasswordChange,
) -> Any:
    """
    Change current user's password.
    """
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    db: DBSession,
    current_user: CurrentUser,
    key_data: APIKeyCreate,
) -> Any:
    """
    Create a new API key for the current user.
    """
    # Generate key
    raw_key = generate_api_key()
    key_prefix = raw_key[:8]
    key_hash = get_password_hash(raw_key)

    # Calculate expiration
    expires_at = None
    if key_data.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)

    api_key = APIKey(
        user_id=current_user.id,
        name=key_data.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        expires_at=expires_at,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only returned on creation
        key_prefix=key_prefix,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/api-keys")
async def list_api_keys(
    db: DBSession,
    current_user: CurrentUser,
) -> Any:
    """
    List current user's API keys.
    """
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    keys = result.scalars().all()

    return [
        {
            "id": key.id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "is_active": key.is_active,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "created_at": key.created_at.isoformat(),
        }
        for key in keys
    ]


@router.delete("/api-keys/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    db: DBSession,
    current_user: CurrentUser,
    key_id: int,
) -> Any:
    """
    Revoke an API key.
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.id == key_id)
        .where(APIKey.user_id == current_user.id)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    return MessageResponse(message="API key revoked successfully")
