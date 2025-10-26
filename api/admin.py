"""
Admin API endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UpdateSubscriptionRequest(BaseModel):
    user_id: int
    active: bool
    sub_type: str
    until: Optional[str] = None


class GrantSubscriptionRequest(BaseModel):
    login: str
    sub_type: str
    days: Optional[int] = None


@router.get("/users")
async def get_all_users(request: Request):
    """Get all users for admin panel"""
    db = request.state.db
    users = await db.get_all_users()
    return {"users": users}


@router.post("/update-subscription")
async def update_user_subscription(data: UpdateSubscriptionRequest, request: Request):
    """Update user subscription"""
    try:
        db = request.state.db
        await db.update_subscription(
            data.user_id,
            data.active,
            data.sub_type,
            data.until
        )
        return {"success": True, "message": "Підписку оновлено"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grant-subscription")
async def grant_subscription_admin(data: GrantSubscriptionRequest, request: Request):
    """Grant subscription to user (ADMIN ONLY)"""
    try:
        db = request.state.db
        user = await db.get_user_by_login(data.login)
        if not user:
            raise HTTPException(status_code=404, detail="Користувач не знайдений")
        
        until = None
        if data.days:
            until_date = datetime.now() + timedelta(days=data.days)
            until = until_date.isoformat()
        
        await db.update_subscription(user['id'], True, data.sub_type, until)
        
        return {
            "success": True,
            "message": f"Підписку виданo користувачу {user['full_name']}",
            "subscription_type": data.sub_type,
            "subscription_until": until
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

