"""
Render Server for Diia Backend
Combines FastAPI API with Telegram Bot Webhook
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
import os
from dotenv import load_dotenv

import cloudinary

# Import bot and database
from bot.handlers import router
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from database.models import Database

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary_url = os.getenv("CLOUDINARY_URL")
if not cloudinary_url:
    raise RuntimeError("CLOUDINARY_URL is not configured")

cloudinary.config(
    cloudinary_url=cloudinary_url,
    secure=True,
)

# Custom JSON encoder for datetime objects
class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Flask app for API endpoints
flask_app = Flask(__name__)
flask_app.json = CustomJSONProvider(flask_app)
CORS(flask_app)

# Telegram Bot setup
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

# Database setup
db_url = os.getenv("DATABASE_URL", "database/diia.db")
db = Database(db_url)

# Middleware to inject database into bot handlers
@dp.message.middleware()
async def db_middleware(handler, event, data):
    """Inject database into handler data"""
    data["db"] = db
    return await handler(event, data)

# Helper function to run async code in sync context
def run_async(coro):
    """Run async coroutine in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Initialize database
async def init_db():
    """Initialize database"""
    os.makedirs("database", exist_ok=True)
    await db.init_db()

# Flask API endpoints (same as FastAPI)
@flask_app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Render server is running"})

@flask_app.route("/keep-alive", methods=["GET"])
def keep_alive():
    """Keep-alive endpoint to prevent sleep on free tier"""
    return jsonify({"status": "ok", "message": "Server is alive"})

@flask_app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Authenticate user"""
    async def _async_login():
        data = request.json
        login = data.get("login")
        password = data.get("password")
        
        logger.info(f"Login attempt for: {login}")
        
        # Get user by login
        user = await db.get_user_by_login(login)
        
        if not user:
            logger.warning(f"User not found: {login}")
            return None, "Невірний логін або пароль"
        
        logger.info(f"User found: {login}, verifying password...")
        
        # Verify password
        password_valid = await db.verify_password(user['password_hash'], password)
        
        if not password_valid:
            logger.warning(f"Invalid password for user: {login}")
            return None, "Невірний логін або пароль"
        
        logger.info(f"Login successful for: {login}")
        
        # Update last login
        await db.update_last_login(user['id'])
        
        # Convert datetime objects to strings
        last_login = user['last_login']
        if isinstance(last_login, datetime):
            last_login = last_login.isoformat()
        
        registered_at = user['registered_at']
        if isinstance(registered_at, datetime):
            registered_at = registered_at.isoformat()
        
        user_safe = {
            "id": user['id'],
            "full_name": user['full_name'],
            "birth_date": user['birth_date'],
            "login": user['login'],
            "subscription_active": bool(user['subscription_active']),
            "subscription_type": user['subscription_type'],
            "last_login": last_login,
            "registered_at": registered_at
        }
        
        return user_safe, None
    
    try:
        user_safe, error = run_async(_async_login())
        
        if error:
            return jsonify({
                "success": False,
                "message": error
            }), 401
        
        return jsonify({
            "success": True,
            "message": "Успішна авторизація",
            "user": user_safe
        })
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "message": "Помилка сервера"}), 500

@flask_app.route("/api/user/<login>", methods=["GET"])
def api_get_user(login):
    """Get user data by login"""
    async def _async_get_user():
        user = await db.get_user_by_login(login)
        
        if not user:
            return None
        
        # photo_path now contains Cloudinary URL
        photo_url = user.get('photo_path')
        
        # Convert datetime objects to strings
        last_login = user['last_login']
        if isinstance(last_login, datetime):
            last_login = last_login.isoformat()
        
        subscription_until = user['subscription_until']
        if isinstance(subscription_until, datetime):
            subscription_until = subscription_until.isoformat()
        
        return {
            "full_name": user['full_name'],
            "birth_date": user['birth_date'],
            "photo_url": photo_url,
            "last_login": last_login,
            "subscription_active": bool(user['subscription_active']),
            "subscription_type": user['subscription_type'],
            "subscription_until": subscription_until
        }
    
    try:
        user_data = run_async(_async_get_user())
        
        if not user_data:
            return jsonify({"error": "Користувач не знайдений"}), 404
        
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/photo/<int:user_id>", methods=["GET"])
def api_get_photo(user_id):
    """Get user photo URL (redirect to Cloudinary)"""
    from flask import redirect
    
    async def _async_get_photo():
        user = await db.get_user_by_id(user_id)
        
        if not user or not user.get('photo_path'):
            return None
        
        return user['photo_path']
    
    try:
        photo_url = run_async(_async_get_photo())
        
        if not photo_url:
            return jsonify({"error": "Фото не знайдено"}), 404
        
        # Redirect to Cloudinary URL
        return redirect(photo_url)
        
    except Exception as e:
        logger.error(f"Get photo error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

# Admin endpoints
@flask_app.route("/api/admin/users", methods=["GET"])
def api_admin_get_users():
    """Get all users (ADMIN)"""
    async def _async_get_users():
        users = await db.get_all_users()
        
        # Convert datetime objects to strings for JSON serialization
        for user in users:
            if user.get('subscription_until') and isinstance(user['subscription_until'], datetime):
                user['subscription_until'] = user['subscription_until'].isoformat()
            if user.get('last_login') and isinstance(user['last_login'], datetime):
                user['last_login'] = user['last_login'].isoformat()
            if user.get('registered_at') and isinstance(user['registered_at'], datetime):
                user['registered_at'] = user['registered_at'].isoformat()
            if user.get('updated_at') and isinstance(user['updated_at'], datetime):
                user['updated_at'] = user['updated_at'].isoformat()
        
        return users
    
    try:
        users = run_async(_async_get_users())
        return jsonify({"users": users})
    except Exception as e:
        logger.error(f"Admin get users error: {e}", exc_info=True)
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/admin/grant-subscription", methods=["POST"])
def api_admin_grant_subscription():
    """Grant subscription (ADMIN)"""
    async def _async_grant():
        data = request.get_json()
        login = data.get('login')
        sub_type = data.get('sub_type')
        days = data.get('days')
        
        user = await db.get_user_by_login(login)
        if not user:
            return None, "Користувач не знайдений"
        
        until = None
        if days:
            until = datetime.now() + timedelta(days=int(days))
        
        await db.update_subscription(user['id'], True, sub_type, until)
        
        return {
            "success": True,
            "message": f"Підписку виданo користувачу {user['full_name']}",
            "subscription_type": sub_type,
            "subscription_until": until.isoformat() if until else None
        }, None
    
    try:
        result, error = run_async(_async_grant())
        
        if error:
            return jsonify({"error": error}), 404
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Grant subscription error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/admin/update-subscription", methods=["POST"])
def api_admin_update_subscription():
    """Update subscription (ADMIN)"""
    async def _async_update():
        data = request.get_json()
        user_id = data.get('user_id')
        active = data.get('active')
        sub_type = data.get('sub_type')
        until_str = data.get('until')
        
        # Convert string to datetime if provided
        until = None
        if until_str:
            try:
                until = datetime.fromisoformat(until_str)
            except:
                return None, "Невірний формат дати"
        
        await db.update_subscription(user_id, active, sub_type, until)
        
        return {
            "success": True,
            "message": "Підписку оновлено"
        }, None
    
    try:
        result, error = run_async(_async_update())
        
        if error:
            return jsonify({"error": error}), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Update subscription error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

# Webhook for Telegram
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Telegram webhook handler"""
    async def _async_webhook():
        update_json = request.json
        update = await bot.session.api._process_update(update_json)
        
        # Process update
        await dp._process_update(update)
        
        return {"ok": True}
    
    try:
        result = run_async(_async_webhook())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# Webhook setup endpoint
@flask_app.route("/set_webhook", methods=["POST"])
def set_webhook_endpoint():
    """Set webhook URL (call once after deploy)"""
    async def _async_set_webhook():
        webhook_url = request.json.get("url")
        
        if not webhook_url:
            return None, "URL required"
        
        try:
            await bot.set_webhook(webhook_url)
            return {"ok": True, "url": webhook_url}, None
        except Exception as e:
            logger.error(f"Set webhook error: {e}")
            return None, str(e)
    
    result, error = run_async(_async_set_webhook())
    
    if error:
        return jsonify({"error": error}), 400 if error == "URL required" else 500
    
    return jsonify(result)

# Startup
async def on_startup():
    """Initialize on startup"""
    await init_db()
    logger.info("Database initialized")

# Aiohttp app for webhook
async def create_webhook_app():
    """Create aiohttp app for webhook"""
    # Simple handler for webhook
    async def webhook_handler(request):
        """Handle webhook requests"""
        update_dict = await request.json()
        telegram_update = await bot.session.api._process_update(update_dict)
        await dp.feed_update(bot, telegram_update)
        return web.Response(text="OK")
    
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    return app

# Main function for Render
if __name__ == "__main__":
    # Initialize on startup
    asyncio.run(on_startup())
    
    # Get port from environment (Render provides this)
    port = int(os.getenv("PORT", 8000))
    
    # Run Flask app
    flask_app.run(host="0.0.0.0", port=port, debug=False)
