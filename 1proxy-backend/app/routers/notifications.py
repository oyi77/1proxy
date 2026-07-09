from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.dependencies import require_user
from app.db_models import User
from app.db_storage import db_storage

router = APIRouter(prefix="/api/v1", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    message: str
    severity: str
    created_at: datetime
    read: bool

    model_config = {"from_attributes": True}


async def create_notification(
    db: AsyncSession,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    severity: str = "info",
):
    await db_storage.create_notification(
        db,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        severity=severity,
    )


@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: User = Depends(require_user),
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get notifications for the current user.

    Returns notifications for the authenticated user.
    Optionally filter to only unread notifications.

    - **Authentication**: Required (any authenticated user)
    - **Returns**: List of notifications
    """
    return await db_storage.get_notifications(
        db, user_id=current_user.id, unread_only=unread_only
    )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notification as read.

    Marks a specific notification as read for the current user.
    Only the notification owner can mark it as read.

    - **Authentication**: Required (owner)
    - **Returns**: Success message
    """
    success = await db_storage.mark_notification_read(
        db, user_id=current_user.id, notification_id=notification_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"message": "Notification marked as read"}


@router.post("/notifications/read-all")
async def mark_all_read(
    current_user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
):
    """
    Mark all notifications as read.

    Marks all notifications for the current user as read.
    Useful for clearing all unread notifications at once.

    - **Authentication**: Required (any authenticated user)
    - **Returns**: Success message with count of marked notifications
    """
    count = await db_storage.mark_all_notifications_read(db, user_id=current_user.id)
    return {"message": f"Marked {count} notifications as read"}
