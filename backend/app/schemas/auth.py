"""
Authentication schemas.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str
    exp: int
    type: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr


class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response (only returned on creation)."""
    id: int
    name: str
    key: str  # Only returned on creation
    key_prefix: str
    expires_at: Optional[str] = None
