from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import os
from urllib.parse import urlencode, urlparse, urlunparse

from app.database import get_db
from app.oauth import oauth_handler
from app.dependencies import get_current_user
from app.db_models import User
from app.config import settings
from app.services.usage import log_usage

router = APIRouter(prefix="/auth", tags=["authentication"])

# Access limiter from app state via request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def _build_frontend_url(
    path: str, query_params: Optional[dict[str, str]] = None
) -> str:
    """Build a frontend URL that preserves an optional basePath.

    GitHub Pages and some reverse proxies host the frontend under a subpath
    (e.g. https://domain.tld/1proxy). In those cases, redirect targets must
    include that prefix.
    """

    base = str(settings.FRONTEND_URL)
    base_path = str(getattr(settings, "FRONTEND_BASE_PATH", ""))

    parsed = urlparse(base)

    base_parts = [p for p in parsed.path.strip("/").split("/") if p]
    base_path_parts = [p for p in base_path.strip("/").split("/") if p]

    # Avoid duplicating the base path if FRONTEND_URL already includes it.
    if base_path_parts and base_parts[-len(base_path_parts) :] == base_path_parts:
        base_path_parts = []

    target_parts = [p for p in path.strip("/").split("/") if p]
    full_path = "/" + "/".join([*base_parts, *base_path_parts, *target_parts])

    query = urlencode(query_params or {})
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            full_path,
            "",
            query,
            "",
        )
    )


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
    """
    Get current authenticated user information.

    Returns the profile information for the currently logged-in user based on the
    access token cookie. If no valid token is present, returns 401 Unauthorized.

    - **Authentication**: Required (cookie-based, set via OAuth login)
    - **Rate limit**: 60 requests/minute
    - **Returns**: User profile with id, email, username, avatar, and role
    """
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
    """
    Initiate GitHub OAuth login flow.

    Redirects the user to GitHub's OAuth authorization page where they can
    grant access to their GitHub account. After authorization, GitHub will
    redirect back to the callback URL with an authorization code.

    - **Authentication**: Not required (this is the login endpoint)
    - **Rate limit**: 10 requests/minute
    - **Scope**: user:email (access to user's email address)
    - **Returns**: Redirect to GitHub OAuth page
    """
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
    """
    Handle GitHub OAuth callback.

    Processes the authorization code received from GitHub after user grants access.
    Exchanges the code for an access token, creates or retrieves the user account,
    and sets an HTTP-only cookie with the JWT access token.

    - **Authentication**: Not required (this completes the login flow)
    - **Rate limit**: 20 requests/minute
    - **Query params**: `code` (authorization code from GitHub)
    - **Returns**: Redirect to dashboard on success, or login page with error
    - **Side effects**: Sets `access_token` cookie, creates user if new
    """
    try:
        user, token = await oauth_handler.github_callback(code, session)
        await log_usage(
            session, user_id=user.id, action="login", resource_type="github"
        )

        response = RedirectResponse(url=_build_frontend_url("/dashboard"))
        secure_cookie = bool(str(settings.FRONTEND_URL).startswith("https"))
        samesite = "none" if secure_cookie else "lax"
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite,
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=_build_frontend_url("/login", {"error": str(e)}))


@router.get("/google")
@limiter.limit("10/minute")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow.

    Redirects the user to Google's OAuth authorization page where they can
    grant access to their Google account. After authorization, Google will
    redirect back to the callback URL with an authorization code.

    - **Authentication**: Not required (this is the login endpoint)
    - **Rate limit**: 10 requests/minute
    - **Scope**: openid email profile
    - **Returns**: Redirect to Google OAuth page
    """
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
    """
    Handle Google OAuth callback.

    Processes the authorization code received from Google after user grants access.
    Exchanges the code for an access token, creates or retrieves the user account,
    and sets an HTTP-only cookie with the JWT access token.

    - **Authentication**: Not required (this completes the login flow)
    - **Rate limit**: 20 requests/minute
    - **Query params**: `code` (authorization code from Google)
    - **Returns**: Redirect to dashboard on success, or login page with error
    - **Side effects**: Sets `access_token` cookie, creates user if new
    """
    try:
        redirect_uri = f"{settings.API_URL}/auth/google/callback"
        user, token = await oauth_handler.google_callback(code, redirect_uri, session)
        await log_usage(
            session, user_id=user.id, action="login", resource_type="google"
        )

        response = RedirectResponse(url=_build_frontend_url("/dashboard"))
        secure_cookie = bool(str(settings.FRONTEND_URL).startswith("https"))
        samesite = "none" if secure_cookie else "lax"
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite,
            max_age=60 * 60 * 24 * 7,
        )

        return response

    except Exception as e:
        return RedirectResponse(url=_build_frontend_url("/login", {"error": str(e)}))


@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, response: Response):
    """
    Logout the current user.

    Clears the `access_token` cookie, effectively logging the user out.
    The client should also remove any stored tokens on their side.

    - **Authentication**: Required (cookie-based)
    - **Rate limit**: 30 requests/minute
    - **Returns**: Success message
    - **Side effects**: Deletes `access_token` cookie
    """
    response = Response(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token")
    return response
