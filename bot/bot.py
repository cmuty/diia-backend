"""
Telegram Bot Main File
"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from bot.handlers import router
from database.models import Database

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start the bot"""
    # Initialize bot and dispatcher
    bot_token = os.getenv("BOT_TOKEN")
    bot = Bot(token=bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Initialize database
    db_path = os.getenv("DATABASE_PATH", "database/diia.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = Database(db_path)
    await db.init_db()
    
    # Register router with middleware to pass db and bot
    @router.message.middleware()
    @router.callback_query.middleware()
    async def db_middleware(handler, event, data):
        data['db'] = db
        data['bot'] = bot
        return await handler(event, data)
    
    dp.include_router(router)
    
    logger.info("Bot started!")
    
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

