"""
API dependencies for authentication, authorization, and common operations.
"""
from typing import Optional, Generator, Annotated
from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token, verify_password
from app.core.config import get_settings
from app.models.user import User, APIKey

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> User:
    """
    Get current authenticated user from JWT token or API key.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try JWT token first
    if token:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception

        if payload.get("type") != "access":
            raise credentials_exception

        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        result = await db.execute(
            select(User)
            .options(selectinload(User.user_roles))
            .where(User.id == int(user_id))
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        return user

    # Try API key
    if api_key:
        # Find API key by prefix (first 8 chars)
        key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
        result = await db.execute(
            select(APIKey)
            .options(selectinload(APIKey.user))
            .where(APIKey.key_prefix == key_prefix)
            .where(APIKey.is_active == True)
        )
        api_key_record = result.scalar_one_or_none()

        if api_key_record is None:
            raise credentials_exception

        # Verify full key hash
        if not verify_password(api_key, api_key_record.key_hash):
            raise credentials_exception

        # Check expiration
        if api_key_record.expires_at:
            from datetime import datetime
            if datetime.utcnow() > api_key_record.expires_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired",
                )

        # Update last used
        from datetime import datetime
        api_key_record.last_used_at = datetime.utcnow()
        await db.commit()

        user = api_key_record.user
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        return user

    raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


class PermissionChecker:
    """
    Dependency for checking user permissions.
    Usage: Depends(PermissionChecker("assets.write"))
    """

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    async def __call__(
        self,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        # Superusers have all permissions
        if current_user.is_superuser:
            return current_user

        # Check user roles for permission
        for user_role in current_user.user_roles:
            result = await db.execute(
                select(user_role.role).options(selectinload(user_role.role.permissions))
            )
            role = result.scalar_one_or_none()
            if role:
                for permission in role.permissions:
                    if permission.code == self.required_permission:
                        return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{self.required_permission}' required",
        )


# Common query parameters
class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size


# Type aliases for cleaner signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
Pagination = Annotated[PaginationParams, Depends()]
