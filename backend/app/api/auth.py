from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database import get_db_session
from app.services.auth import (
    get_current_user,
    login,
    logout,
    refresh_token,
    oidc_login,
)
from app.core.config import settings
from app.services.oidc import get_authorization_url
from urllib.parse import urlencode

from app.models import User
router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str]


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    result = await login(session, request.username, request.password)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("error"))
    return result


@router.get("/auth/login")
async def oidc_login_init(
    redirect_uri: str = "http://localhost:3000/callback",
) -> dict:
    """Initiate OIDC authorization-code flow with PKCE."""
    auth_url, state = get_authorization_url(redirect_uri)
    # In a real app, you'd set a cookie or session state here
    # For now, return the auth URL and state for the frontend to redirect
    return {"authorization_url": auth_url, "state": state}


@router.get("/auth/callback")
async def oidc_login_callback(
    code: str,
    state: str,
    redirect_uri: str = "http://localhost:3000/callback",
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Handle OIDC callback with authorization code."""
    # Exchange code for tokens and get user info
    result = await oidc_login(session, code, state, redirect_uri)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error"),
        )
    # In production, set HttpOnly SameSite cookies here
    # For now, return tokens and user info
    return {
        "success": True,
        "access_token": result["access_token"],
        "token_type": result["token_type"],
        "user": {
            "id": result.get("user_id", ""),
            "username": result.get("username", ""),
            "email": result.get("email", ""),
            "roles": result.get("roles", []),
        },
    }
async def logout_endpoint() -> dict:
    return {"success": True}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
):
    result = await refresh_token(session, request.refresh_token)
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=result.get("error"))
    return result


@router.get("/me", response_model=UserResponse)
async def me(
    authorization: str | None = Header(None),
    session: AsyncSession = Depends(get_db_session),
):
    current_user = await get_current_user(session, authorization)
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
    }
