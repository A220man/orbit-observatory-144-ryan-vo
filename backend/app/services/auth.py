from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from app.models import User
from app.core.config import settings
from fastapi import HTTPException, status
from jose import jwt
import hashlib
from datetime import datetime, timedelta


async def login(
    session: AsyncSession,
    username: str,
    password: str,
) -> Dict[str, Any]:
    """Authenticate user and return tokens."""
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return {"success": False, "error": "Invalid credentials"}

    # Simple password check (in production use bcrypt)
    if not _verify_password(password, user.password_hash):
        return {"success": False, "error": "Invalid credentials"}

    access_token = _create_token(user, "access", timedelta(minutes=30))
    refresh_token = _create_token(user, "refresh", timedelta(days=7))

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


async def logout(session: AsyncSession, user_id: str) -> None:
    """Logout user (token blacklist would go here)."""
    pass


async def refresh_token(session: AsyncSession, refresh_token: str) -> Dict[str, Any]:
    """Refresh access token."""
    payload = _decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return {"success": False, "error": "Invalid refresh token"}

    stmt = select(User).where(User.id == payload.get("sub"))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return {"success": False, "error": "User not found"}

    access_token = _create_token(user, "access", timedelta(minutes=30))
    new_refresh_token = _create_token(user, "refresh", timedelta(days=7))

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


async def get_current_user(
    session: AsyncSession,
    authorization: Optional[str] = None,
) -> User:
    """Get current user from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[7:]
    payload = _decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == payload.get("sub"))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def _create_token(user: User, token_type: str, expires_delta: timedelta) -> str:
    """Create JWT token."""
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "sub": user.id,
        "username": user.username,
        "roles": user.roles,
        "type": token_type,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.oidc_client_secret or "dev-secret", algorithm="HS256")


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode JWT token."""
    try:
        payload = jwt.decode(token, settings.oidc_client_secret or "dev-secret", algorithms=["HS256"])
        return payload
    except jwt.JWTError:
        return None


def _verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def _hash_password(password: str) -> str:
    """Hash password."""
    return hashlib.sha256(password.encode()).hexdigest()