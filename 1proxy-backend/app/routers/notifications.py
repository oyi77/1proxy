from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.dependencies import require_user
from app.db_models import User

router = APIRouter(prefix="/api/v1", tags=["notifications"])


class Notification(BaseModel):
    id: str
    type: str
    title: str
    message: str
    severity: str
    created_at: datetime
    read: bool


notifications_store: dict[int, List[Notification]] = {}


async def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    severity: str = "info",
):
    if user_id not in notifications_store:
        notifications_store[user_id] = []

    notification = Notification(
        id=f"{user_id}_{datetime.utcnow().timestamp()}",
        type=notification_type,
        title=title,
        message=message,
        severity=severity,
        created_at=datetime.utcnow(),
        read=False,
    )

    notifications_store[user_id].insert(0, notification)

    if len(notifications_store[user_id]) > 50:
        notifications_store[user_id] = notifications_store[user_id][:50]


@router.get("/notifications", response_model=List[Notification])
async def get_notifications(
    current_user: User = Depends(require_user), unread_only: bool = False
):
    user_notifications = notifications_store.get(current_user.id, [])

    if unread_only:
        return [n for n in user_notifications if not n.read]

    return user_notifications


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str, current_user: User = Depends(require_user)
):
    user_notifications = notifications_store.get(current_user.id, [])

    for notification in user_notifications:
        if notification.id == notification_id:
            notification.read = True
            return {"message": "Notification marked as read"}

    return {"error": "Notification not found"}


@router.post("/notifications/read-all")
async def mark_all_read(current_user: User = Depends(require_user)):
    user_notifications = notifications_store.get(current_user.id, [])

    for notification in user_notifications:
        notification.read = True

    return {"message": f"Marked {len(user_notifications)} notifications as read"}
