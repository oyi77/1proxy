from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
import logging

from app.db_models import Notification

logger = logging.getLogger(__name__)


class NotificationRepository:
    async def create_notification(
        self,
        session: AsyncSession,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        severity: str = "info",
    ):
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            severity=severity,
        )
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
        return notification

    async def get_notifications(
        self,
        session: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50,
    ):
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read.is_(False))
        query = query.order_by(Notification.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def mark_notification_read(
        self, session: AsyncSession, user_id: int, notification_id: int
    ) -> bool:
        result = await session.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id, Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read = True
            await session.commit()
            return True
        return False

    async def mark_all_notifications_read(
        self, session: AsyncSession, user_id: int
    ) -> int:
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read.is_(False)))
            .values(read=True)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount
