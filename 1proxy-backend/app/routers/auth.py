from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import os

from app.database import get_db
from app.oauth import oauth_handler
from app.dependencies import get_current_user
from app.db_models import User
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

# Access limiter from app state via request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    avatar_url: Optional[str]
    role: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserInfo)
@limiter.limit("60/minute")
async def get_current_user_info(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
    )


@router.get("/github")
@limiter.limit("10/minute")
async def github_login(request: Request):
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=user:email"
    )


@router.get("/github/callback")
@limiter.limit("20/minute")
async def github_callback(
    request: Request,
    code: str,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    try:
        user, token = await oauth_handler.github_callback(code, session)

        response = RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True if settings.FRONTEND_URL.startswith("https") else False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={str(e)}")


@router.get("/google")
@limiter.limit("10/minute")
async def google_login(request: Request):
    google_client_id = settings.GOOGLE_CLIENT_ID
    redirect_uri = f"{settings.API_URL}/auth/google/callback"

    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={google_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile"
    )


@router.get("/google/callback")
@limiter.limit("20/minute")
async def google_callback(
    request: Request,
    code: str,
    response: Response,
    session: AsyncSession = Depends(get_db),
):
    try:
        redirect_uri = f"{settings.API_URL}/auth/google/callback"
        user, token = await oauth_handler.google_callback(code, redirect_uri, session)

        response = RedirectResponse(url=f"{settings.FRONTEND_URL}/dashboard")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True if settings.FRONTEND_URL.startswith("https") else False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error={str(e)}")


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, response: Response):
    response = Response(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response
