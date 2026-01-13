from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import os

from app.database import get_db
from app.oauth import oauth_handler
from app.dependencies import get_current_user
from app.db_models import User

router = APIRouter(prefix="/auth", tags=["authentication"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")


class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    avatar_url: Optional[str]
    role: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
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
async def github_login():
    return RedirectResponse(
        url=f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=user:email"
    )


@router.get("/github/callback")
async def github_callback(
    code: str, response: Response, session: AsyncSession = Depends(get_db)
):
    try:
        user, token = await oauth_handler.github_callback(code, session)

        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True if FRONTEND_URL.startswith("https") else False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error={str(e)}")


@router.get("/google")
async def google_login():
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    redirect_uri = (
        f"{os.getenv('API_URL', 'http://localhost:8000')}/auth/google/callback"
    )

    return RedirectResponse(
        url=f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={google_client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope=openid email profile"
    )


@router.get("/google/callback")
async def google_callback(
    code: str, response: Response, session: AsyncSession = Depends(get_db)
):
    try:
        redirect_uri = (
            f"{os.getenv('API_URL', 'http://localhost:8000')}/auth/google/callback"
        )
        user, token = await oauth_handler.google_callback(code, redirect_uri, session)

        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=True if FRONTEND_URL.startswith("https") else False,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error={str(e)}")


@router.post("/logout")
async def logout(response: Response):
    response = Response(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response
