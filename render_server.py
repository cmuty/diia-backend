"""
Render Server for Diia Backend
Combines FastAPI API with Telegram Bot Webhook
"""
import asyncio
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
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

# Flask app for API endpoints
flask_app = Flask(__name__)
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
async def api_login():
    """Authenticate user"""
    try:
        data = request.json
        login = data.get("login")
        password = data.get("password")
        
        # Get user by login
        user = await db.get_user_by_login(login)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "Невірний логін або пароль"
            }), 401
        
        # Verify password
        password_valid = await db.verify_password(user['password_hash'], password)
        
        if not password_valid:
            return jsonify({
                "success": False,
                "message": "Невірний логін або пароль"
            }), 401
        
        # Update last login
        await db.update_last_login(user['id'])
        
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
        
        return jsonify({
            "success": True,
            "message": "Успішна авторизація",
            "user": user_safe
        })
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "message": "Помилка сервера"}), 500

@flask_app.route("/api/user/<login>", methods=["GET"])
async def api_get_user(login):
    """Get user data by login"""
    try:
        user = await db.get_user_by_login(login)
        
        if not user:
            return jsonify({"error": "Користувач не знайдений"}), 404
        
        # photo_path now contains Cloudinary URL
        photo_url = user.get('photo_path')
        
        return jsonify({
            "full_name": user['full_name'],
            "birth_date": user['birth_date'],
            "photo_url": photo_url,
            "last_login": user['last_login'],
            "subscription_active": bool(user['subscription_active']),
            "subscription_type": user['subscription_type'],
            "subscription_until": user['subscription_until']
        })
        
    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/photo/<int:user_id>", methods=["GET"])
async def api_get_photo(user_id):
    """Get user photo URL (redirect to Cloudinary)"""
    from flask import redirect
    try:
        user = await db.get_user_by_id(user_id)
        
        if not user or not user.get('photo_path'):
            return jsonify({"error": "Фото не знайдено"}), 404
        
        # Redirect to Cloudinary URL
        return redirect(user['photo_path'])
        
    except Exception as e:
        logger.error(f"Get photo error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

# Admin endpoints
@flask_app.route("/api/admin/users", methods=["GET"])
async def api_admin_get_users():
    """Get all users (ADMIN)"""
    try:
        users = await db.get_all_users()
        return jsonify({"users": users})
    except Exception as e:
        logger.error(f"Admin get users error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/admin/grant-subscription", methods=["POST"])
async def api_admin_grant_subscription():
    """Grant subscription (ADMIN)"""
    try:
        data = request.get_json()
        login = data.get('login')
        sub_type = data.get('sub_type')
        days = data.get('days')
        
        user = await db.get_user_by_login(login)
        if not user:
            return jsonify({"error": "Користувач не знайдений"}), 404
        
        until = None
        if days:
            until_date = datetime.now() + timedelta(days=int(days))
            until = until_date.isoformat()
        
        await db.update_subscription(user['id'], True, sub_type, until)
        
        return jsonify({
            "success": True,
            "message": f"Підписку виданo користувачу {user['full_name']}",
            "subscription_type": sub_type,
            "subscription_until": until
        })
    except Exception as e:
        logger.error(f"Grant subscription error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

@flask_app.route("/api/admin/update-subscription", methods=["POST"])
async def api_admin_update_subscription():
    """Update subscription (ADMIN)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        active = data.get('active')
        sub_type = data.get('sub_type')
        until = data.get('until')
        
        await db.update_subscription(user_id, active, sub_type, until)
        
        return jsonify({
            "success": True,
            "message": "Підписку оновлено"
        })
    except Exception as e:
        logger.error(f"Update subscription error: {e}")
        return jsonify({"error": "Помилка сервера"}), 500

# Webhook for Telegram
@flask_app.route("/webhook", methods=["POST"])
async def webhook():
    """Telegram webhook handler"""
    try:
        update_json = request.json
        update = await bot.session.api._process_update(update_json)
        
        # Create aiohttp request for bot handler
        bot_request = request.get_json()
        
        # Process update
        await dp._process_update(update)
        
        return jsonify({"ok": True})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# Webhook setup endpoint
@flask_app.route("/set_webhook", methods=["POST"])
async def set_webhook_endpoint():
    """Set webhook URL (call once after deploy)"""
    webhook_url = request.json.get("url")
    
    if not webhook_url:
        return jsonify({"error": "URL required"}), 400
    
    try:
        await bot.set_webhook(webhook_url)
        return jsonify({"ok": True, "url": webhook_url})
    except Exception as e:
        logger.error(f"Set webhook error: {e}")
        return jsonify({"error": str(e)}), 500

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
