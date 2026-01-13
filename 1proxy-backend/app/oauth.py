import os
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_models import User
from app.auth import create_access_token

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


class OAuthHandler:
    @staticmethod
    async def github_callback(code: str, session: AsyncSession) -> tuple[User, str]:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
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

            result = await session.execute(
                select(User).where(
                    User.oauth_provider == "github",
                    User.oauth_id == str(github_user["id"]),
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                user = User(
                    oauth_provider="github",
                    oauth_id=str(github_user["id"]),
                    email=github_user.get("email")
                    or f"{github_user['login']}@github.local",
                    username=github_user["login"],
                    avatar_url=github_user.get("avatar_url"),
                    role="user",
                )
                session.add(user)
            else:
                user.last_login = None
                user.username = github_user["login"]
                user.avatar_url = github_user.get("avatar_url")

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
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
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
