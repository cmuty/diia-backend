"""
FastAPI Server for iOS App Authentication
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from database.models import Database
from api.admin import router as admin_router

load_dotenv()

app = FastAPI(title="Diia Backend API")

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db_url = os.getenv("DATABASE_URL", "database/diia.db")
db = Database(db_url)

# Middleware to inject db into request state
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    request.state.db = db
    response = await call_next(request)
    return response

# Include admin router
app.include_router(admin_router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    os.makedirs("database", exist_ok=True)
    await db.init_db()


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None


class UserDataResponse(BaseModel):
    full_name: str
    birth_date: str
    photo_url: Optional[str]
    last_login: Optional[str]
    subscription_active: bool
    subscription_type: str
    subscription_until: Optional[str]


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Authenticate user
    iOS app will call this endpoint with login and password
    """
    # Get user by login
    user = await db.get_user_by_login(request.login)
    
    if not user:
        return LoginResponse(
            success=False,
            message="Невірний логін або пароль"
        )
    
    # Verify password
    password_valid = await db.verify_password(user['password_hash'], request.password)
    
    if not password_valid:
        return LoginResponse(
            success=False,
            message="Невірний логін або пароль"
        )
    
    # Update last login
    await db.update_last_login(user['id'])
    
    # Remove sensitive data
    user_safe = {
        "id": user['id'],
        "full_name": user['full_name'],
        "birth_date": user['birth_date'],
        "login": user['login'],
        "subscription_active": bool(user['subscription_active']),
        "subscription_type": user['subscription_type'],
        "last_login": user['last_login'],
        "registered_at": user['registered_at']
    }
    
    return LoginResponse(
        success=True,
        message="Успішна авторизація",
        user=user_safe
    )


@app.get("/api/user/{login}", response_model=UserDataResponse)
async def get_user_data(login: str):
    """
    Get user data by login
    """
    user = await db.get_user_by_login(login)
    
    if not user:
        raise HTTPException(status_code=404, detail="Користувач не знайдений")
    
    # photo_path now contains Cloudinary URL
    photo_url = user.get('photo_path')
    
    return UserDataResponse(
        full_name=user['full_name'],
        birth_date=user['birth_date'],
        photo_url=photo_url,
        last_login=user['last_login'],
        subscription_active=bool(user['subscription_active']),
        subscription_type=user['subscription_type'],
        subscription_until=user['subscription_until']
    )


@app.get("/api/photo/{user_id}")
async def get_user_photo(user_id: int):
    """
    Get user photo by user ID (redirect to Cloudinary)
    """
    from fastapi.responses import RedirectResponse
    
    user = await db.get_user_by_id(user_id)
    
    if not user or not user.get('photo_path'):
        raise HTTPException(status_code=404, detail="Фото не знайдено")
    
    # Redirect to Cloudinary URL
    return RedirectResponse(url=user['photo_path'])


@app.get("/api/admin/users")
async def get_all_users_admin():
    """
    Get all users (ADMIN ONLY - add auth later)
    """
    users = await db.get_all_users()
    return {"users": users}


@app.post("/api/admin/grant-subscription")
async def grant_subscription_admin(login: str, sub_type: str, days: int = None):
    """
    Grant subscription to user (ADMIN ONLY - add auth later)
    """
    user = await db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="Користувач не знайдений")
    
    until = None
    if days:
        until_date = datetime.now() + timedelta(days=days)
        until = until_date.isoformat()
    
    await db.update_subscription(user['id'], True, sub_type, until)
    
    return {
        "success": True,
        "message": f"Підписку виданo користувачу {user['full_name']}",
        "subscription_type": sub_type,
        "subscription_until": until
    }


@app.post("/api/admin/update-subscription")
async def update_subscription_admin(user_id: int, active: bool, sub_type: str, until: str = None):
    """
    Update user subscription (ADMIN ONLY)
    """
    await db.update_subscription(user_id, active, sub_type, until)
    
    return {
        "success": True,
        "message": "Підписку оновлено"
    }


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok", "message": "Server is running"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    uvicorn.run(app, host=host, port=port)

