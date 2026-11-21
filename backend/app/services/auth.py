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
async def oidc_login(
    session: AsyncSession,
    code: str,
    state: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """Login via OIDC authorization-code flow with PKCE."""
    from authlib.integrations.oauth2.rfc6749.parameters import CodeChallengeMethod
    from authlib.jose import JsonWebKey
    from authlib.jose.rfc7519 import JsonWebToken
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    from app.models import User
    from app.services.oidc import exchange_code, map_keycloak_roles
    from app.core.config import settings
    import httpx
    
    # Exchange authorization code for tokens
    token_response = await exchange_code(code, state)
    
    id_token_payload = token_response.get("id_token_payload")
    if not id_token_payload:
        return {"success": False, "error": "No ID token in response"}
    
    # Get the user's sub (subject/ID) from the token
    user_sub = id_token_payload.get("sub")
    if not user_sub:
        return {"success": False, "error": "No sub in ID token"}
    
    # Check if user exists; create if not (for OIDC)
    stmt = select(User).where(User.id == user_sub)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user from OIDC claims
        username = id_token_payload.get("preferred_username") or id_token_payload.get("email", "oidc-user")
        email = id_token_payload.get("email", "")
        # Use a default role or extract from token
        realm_roles = id_token_payload.get("realm_access", {}).get("roles", [])
        user_roles = map_keycloak_roles(realm_roles)
        if not user_roles:
            user_roles = ["viewer"]  # default role
        
        user = User(
            id=user_sub,
            username=username,
            email=email,
            roles=user_roles,
            password_hash="",  # no password for OIDC-only users
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    # Create access and refresh tokens
    access_token = _create_token(user, "access", timedelta(minutes=30))
    refresh_token = _create_token(user, "refresh", timedelta(days=7))
    
    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
