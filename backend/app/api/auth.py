from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database import get_db_session
from app.services.auth import (
    get_current_user,
    login,
    logout,
    refresh_token,
)

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


@router.post("/logout")
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
