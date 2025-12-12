"""
Render Server for Diia Backend
Combines FastAPI API with Telegram Bot Webhook
"""
import asyncio
import logging
import json
import threading
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

# Global event loop for async operations
loop = None

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
    """Run async coroutine in background event loop"""
    global loop, _initialized
    
    # Убеждаемся, что event loop инициализирован
    if loop is None:
        ensure_initialized()
        # Ждем инициализации
        import time
        for _ in range(10):  # Ждем до 10 секунд
            if loop is not None:
                break
            time.sleep(1)
        
        if loop is None:
            raise RuntimeError("Event loop not initialized")
    
    try:
        logger.debug(f"🔄 Running async operation in event loop...")
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        logger.debug(f"⏳ Waiting for async operation to complete (timeout: 30s)...")
        result = future.result(timeout=30)
        logger.debug(f"✅ Async operation completed")
        return result
    except TimeoutError as e:
        logger.error(f"❌ Timeout waiting for async operation (30s exceeded)")
        logger.error(f"Operation: {coro}")
        raise
    except Exception as e:
        logger.error(f"❌ Error in run_async: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def start_background_loop(loop):
    """Start the event loop in a background thread"""
    try:
        logger.info("🔄 Starting event loop in background thread...")
        asyncio.set_event_loop(loop)
        logger.info("✅ Event loop set, starting run_forever...")
        loop.run_forever()
    except Exception as e:
        logger.error(f"❌ Error in event loop: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

# Initialize database
async def init_db():
    """Initialize database"""
    try:
        logger.info(f"📊 Database URL: {db.db_url[:50]}... (PostgreSQL: {db.is_postgres})")
        if not db.is_postgres:
            os.makedirs("database", exist_ok=True)
        logger.info("🔄 Initializing database tables...")
        await db.init_db()
        logger.info("✅ Database tables initialized")
        
        # Проверяем подключение к базе данных
        if db.is_postgres:
            logger.info("🔌 Testing PostgreSQL connection...")
            await db.connect()
            if db.pool:
                logger.info("✅ PostgreSQL connection pool is ready")
            else:
                logger.error("❌ PostgreSQL connection pool is None!")
        else:
            logger.info(f"📁 Using SQLite database: {db.db_path}")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# Flask API endpoints (same as FastAPI)
@flask_app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    logger.info("✅ Health check requested")
    response = jsonify({"status": "ok", "message": "Render server is running"})
    # Добавляем CORS headers для iOS приложения
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

@flask_app.route("/keep-alive", methods=["GET"])
def keep_alive():
    """Keep-alive endpoint to prevent sleep on free tier"""
    return jsonify({"status": "ok", "message": "Server is alive"})

@flask_app.route("/api/auth/login", methods=["POST"])
def api_login():
    """Authenticate user"""
    async def _async_login():
        try:
            data = request.json
            if not data:
                logger.error("No JSON data in request")
                return None, "Невірний формат запиту"
            
            login = data.get("login")
            password = data.get("password")
            
            if not login or not password:
                logger.error(f"Missing login or password. Login: {login}, Password: {'*' * len(password) if password else 'None'}")
                return None, "Логін та пароль обов'язкові"
            
            logger.info(f"Login attempt for: {login}")
            
            # Проверяем, что база данных подключена
            if db.is_postgres:
                if not db.pool:
                    logger.info(f"Database pool not initialized, connecting...")
                    await db.connect()
                logger.info(f"Database pool ready")
            
            # Get user by login
            logger.info(f"Querying database for user: {login}")
            user = await db.get_user_by_login(login)
            logger.info(f"Database query completed for user: {login}")
            
            if not user:
                logger.warning(f"User not found: {login}")
                return None, "Невірний логін або пароль"
            
            logger.info(f"User found: {login}, ID: {user.get('id')}, verifying password...")
            
            # Check if password_hash exists
            password_hash = user.get('password_hash')
            if not password_hash:
                logger.error(f"User {login} has no password_hash!")
                return None, "Помилка: користувач не має паролю"
            
            # Verify password
            logger.info(f"Verifying password for user: {login}")
            password_valid = await db.verify_password(password_hash, password)
            
            if not password_valid:
                logger.warning(f"Invalid password for user: {login}")
                return None, "Невірний логін або пароль"
            
            logger.info(f"Login successful for: {login}")
            
            # Update last login
            try:
                await db.update_last_login(user['id'])
            except Exception as e:
                logger.warning(f"Failed to update last_login: {e}")
            
            # Convert datetime objects to strings
            last_login = user.get('last_login')
            if isinstance(last_login, datetime):
                last_login = last_login.isoformat()
            elif last_login is None:
                last_login = None
            
            registered_at = user.get('registered_at')
            if isinstance(registered_at, datetime):
                registered_at = registered_at.isoformat()
            elif registered_at is None:
                registered_at = None
            
            user_safe = {
                "id": user['id'],
                "full_name": user.get('full_name', ''),
                "birth_date": user.get('birth_date', ''),
                "login": user.get('login', ''),
                "subscription_active": bool(user.get('subscription_active', False)),
                "subscription_type": user.get('subscription_type', 'none'),
                "last_login": last_login,
                "registered_at": registered_at
            }
            
            return user_safe, None
        except Exception as e:
            import traceback
            logger.error(f"Error in _async_login: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
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
        import traceback
        logger.error(f"Login error: {e}")
        logger.error(f"Login error traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Помилка сервера: {str(e)}"}), 500

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
    try:
        logger.info("🔄 Starting database initialization...")
        await init_db()
        logger.info("✅ Database initialization completed")
    except Exception as e:
        logger.error(f"❌ Error in on_startup: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

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

# Global initialization state
_initialized = False
_initializing = False

# Initialize background event loop and database when module is loaded (for gunicorn)
def init_app():
    """Initialize event loop and database (lazy initialization)"""
    global loop, _initialized, _initializing
    
    if _initialized:
        return
    
    if _initializing:
        # Ждем пока инициализация завершится
        import time
        for _ in range(60):  # Ждем до 60 секунд
            if _initialized:
                return
            time.sleep(1)
        return
    
    _initializing = True
    
    try:
        if loop is None:
            logger.info("🚀 Initializing background event loop...")
            # Create a new event loop for background tasks
            loop = asyncio.new_event_loop()
            logger.info("✅ Event loop created")
            
            # Start the event loop in a background thread
            thread = threading.Thread(target=start_background_loop, args=(loop,), daemon=True)
            thread.start()
            logger.info("✅ Event loop thread started")
            
            # Даем event loop время на запуск
            import time
            time.sleep(1)
        
        # Initialize database in the background loop
        logger.info("📊 Initializing database...")
        try:
            # Даем event loop немного времени на запуск
            import time
            time.sleep(2)
            
            future = asyncio.run_coroutine_threadsafe(on_startup(), loop)
            future.result(timeout=120)
            _initialized = True
            logger.info("✅ Application initialized successfully!")
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            _initializing = False
            raise
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}")
        _initializing = False
        raise

def ensure_initialized():
    """Ensure app is initialized (lazy initialization)"""
    global loop, _initialized
    
    if _initialized:
        return
    
    if _initializing:
        # Ждем завершения инициализации
        import time
        for _ in range(60):
            if _initialized:
                return
            time.sleep(1)
        return
    
    # Инициализируем синхронно, если еще не начали
    if not _initializing:
        init_app()

# Initialize on module load (в фоне, не блокируем)
threading.Thread(target=init_app, daemon=True).start()

# Main function for Render (for local development with python server.py)
if __name__ == "__main__":
    # Get port from environment (Render provides this)
    port = int(os.getenv("PORT", 8000))
    
    # Run Flask app
    flask_app.run(host="0.0.0.0", port=port, debug=False)
