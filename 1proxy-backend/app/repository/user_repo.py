from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional
import logging

from app.db_models import User

logger = logging.getLogger(__name__)


class UserRepository:
    async def create_admin_user(
        self, session: AsyncSession, email: str = "admin@1proxy.local"
    ) -> User:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                oauth_provider="local",
                oauth_id="admin",
                email=email,
                username="admin",
                role="admin",
                avatar_url=None,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def get_or_create_user(
        self,
        session: AsyncSession,
        oauth_provider: str,
        oauth_id: str,
        email: str,
        username: str,
        role: str = "user",
        avatar_url: Optional[str] = None,
    ) -> User:
        result = await session.execute(
            select(User).where(
                and_(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                oauth_provider=oauth_provider,
                oauth_id=oauth_id,
                email=email,
                username=username,
                role=role,
                avatar_url=avatar_url,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user

    async def count_users(self, session: AsyncSession) -> int:
        result = await session.execute(select(func.count()).select_from(User))
        return result.scalar() or 0
