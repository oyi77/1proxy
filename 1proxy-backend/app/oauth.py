import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_models import User
from app.auth import create_access_token
from app.config import settings


async def check_github_repo_admin(access_token: str, username: str) -> bool:
    """
    Check if user is admin/owner/collaborator of the configured GitHub repo.
    Returns True if user has admin privileges on the repo.
    """
    if not settings.GITHUB_REPO_OWNER or not settings.GITHUB_REPO_NAME:
        return False

    async with httpx.AsyncClient() as client:
        # Check if user is a collaborator
        collab_response = await client.get(
            f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/collaborators/{username}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if collab_response.status_code == 200:
            collab_data = collab_response.json()
            permission = collab_data.get("permission", "")
            # Admin permissions: admin, maintain, triage
            if permission in ["admin", "maintain", "triage"]:
                return True

        # Check if user is the repo owner (for organization repos)
        repo_response = await client.get(
            f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )

        if repo_response.status_code == 200:
            repo_data = repo_response.json()
            # Check if user is the owner
            if repo_data.get("owner", {}).get("login") == username:
                return True

        return False


class OAuthHandler:
    @staticmethod
    async def github_callback(code: str, session: AsyncSession) -> tuple[User, str]:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="GitHub OAuth failed")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to fetch GitHub user"
                )

            github_user = user_response.json()
            github_username = github_user["login"]
            github_id = str(github_user["id"])

            # Check if user is admin of the configured repo
            is_repo_admin = await check_github_repo_admin(access_token, github_username)

            result = await session.execute(
                select(User).where(
                    User.oauth_provider == "github",
                    User.oauth_id == github_id,
                )
            )
            user = result.scalar_one_or_none()

            # Determine role: admin if repo collaborator, otherwise user
            role = "admin" if is_repo_admin else "user"

            if not user:
                user = User(
                    oauth_provider="github",
                    oauth_id=github_id,
                    email=github_user.get("email") or f"{github_username}@github.local",
                    username=github_username,
                    avatar_url=github_user.get("avatar_url"),
                    role=role,
                )
                session.add(user)
            else:
                user.last_login = None
                user.username = github_username
                user.avatar_url = github_user.get("avatar_url")
                user.role = role  # Update role based on repo access

            await session.commit()
            await session.refresh(user)

            jwt_token = create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role}
            )

            return user, jwt_token

    @staticmethod
    async def google_callback(
        code: str, redirect_uri: str, session: AsyncSession
    ) -> tuple[User, str]:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Google OAuth failed")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=400, detail="Failed to fetch Google user"
                )

            google_user = user_response.json()

            result = await session.execute(
                select(User).where(
                    User.oauth_provider == "google", User.oauth_id == google_user["id"]
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    oauth_provider="google",
                    oauth_id=google_user["id"],
                    email=google_user["email"],
                    username=google_user.get(
                        "name", google_user["email"].split("@")[0]
                    ),
                    avatar_url=google_user.get("picture"),
                    role="user",
                )
                session.add(user)
            else:
                user.last_login = None
                user.username = google_user.get("name", user.username)
                user.avatar_url = google_user.get("picture")

            await session.commit()
            await session.refresh(user)

            jwt_token = create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role}
            )

            return user, jwt_token


oauth_handler = OAuthHandler()
