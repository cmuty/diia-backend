"""
Admin API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateSubscriptionRequest(BaseModel):
    user_id: int
    active: bool
    subscription_type: str
    subscription_until: Optional[str] = None


@router.get("/users")
async def get_all_users(db):
    """Get all users for admin panel"""
    users = await db.get_all_users()
    return {"success": True, "users": users}


@router.post("/subscription")
async def update_user_subscription(request: UpdateSubscriptionRequest, db):
    """Update user subscription"""
    try:
        await db.update_subscription(
            request.user_id,
            request.active,
            request.subscription_type,
            request.subscription_until
        )
        return {"success": True, "message": "Підписку оновлено"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

