"""
FastAPI Server for iOS App Authentication
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import os
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
db_path = os.getenv("DATABASE_PATH", "database/diia.db")
db = Database(db_path)

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
    user = await db.verify_password(request.login, request.password)
    
    if user:
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
    else:
        return LoginResponse(
            success=False,
            message="Невірний логін або пароль"
        )


@app.get("/api/user/{login}", response_model=UserDataResponse)
async def get_user_data(login: str):
    """
    Get user data by login
    """
    user = await db.get_user_by_login(login)
    
    if not user:
        raise HTTPException(status_code=404, detail="Користувач не знайдений")
    
<<<<<<< HEAD
    # photo_path now contains Cloudinary URL
    photo_url = user.get('photo_path')
=======
    # Construct photo URL if exists
    photo_url = user.get('photo_url')
>>>>>>> fc3f77f8e72d26fd8547e579079423bca689694d
    
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

