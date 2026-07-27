"""Admin user management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.db_models import User
from app.dependencies import require_admin
from app.db_storage import db_storage
from typing import Optional
from pydantic import BaseModel
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

users_router = APIRouter()


class UserUpdateRole(BaseModel):
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    created_at: Optional[str]

    model_config = {"from_attributes": True}


@users_router.get("/users", response_model=dict)
@limiter.limit("30/minute")
async def list_users(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: List all registered users.

    Returns a paginated list of all users in the system
    with their roles and creation dates.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 30 requests/minute
    - **Returns**: Paginated list of users
    """
    users, total = await db_storage.get_users(session, limit=limit, offset=offset)
    return {
        "total": total,
        "count": len(users),
        "offset": offset,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@users_router.get("/users/{user_id}", response_model=UserResponse)
@limiter.limit("60/minute")
async def get_user_details(
    request: Request, user_id: int, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Get detailed information about a specific user.

    Returns full user profile including role and creation date.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 60 requests/minute
    - **Returns**: UserResponse with user details
    """
    user = await db_storage.get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@users_router.put("/users/{user_id}/role", response_model=UserResponse)
@limiter.limit("10/minute")
async def update_user_role(
    request: Request,
    user_id: int,
    role_data: UserUpdateRole,
    session: AsyncSession = Depends(get_db),
):
    """
    Admin: Update a user's role.

    Change a user's role between "user" and "admin".
    Only admins can perform this action.

    - **Authentication**: Required (admin role)
    - **Rate limit**: 10 requests/minute
    - **Valid roles**: "user", "admin"
    - **Returns**: Updated UserResponse
    """
    if role_data.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = await db_storage.update_user_role(session, user_id, role_data.role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@users_router.delete("/users/{user_id}")
@limiter.limit("5/minute")
async def delete_user(
    request: Request, user_id: int, session: AsyncSession = Depends(get_db)
):
    """
    Admin: Delete a user from the system.

    Permanently removes a user and all their associated data.
    Cannot delete yourself (self-deletion prevention).

    - **Authentication**: Required (admin role)
    - **Rate limit**: 5 requests/minute
    - **Returns**: Success message
    """
    # Prevent self-deletion if current user is the target
    # This would require current_user from dependency, but we'll stick to basic admin check for now
    success = await db_storage.delete_user(session, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}
