"""
Quick script to check users in database
"""
import asyncio
import os
from dotenv import load_dotenv
from database.models import Database

load_dotenv()

async def main():
    db_url = os.getenv("DATABASE_URL", "database/diia.db")
    print(f"Connecting to: {db_url[:50]}...")
    
    db = Database(db_url)
    await db.init_db()
    
    users = await db.get_all_users()
    
    print(f"\n📊 Total users: {len(users)}\n")
    
    for user in users:
        print(f"ID: {user['id']}")
        print(f"  Telegram ID: {user['telegram_id']}")
        print(f"  ПІБ: {user['full_name']}")
        print(f"  Логін: {user['login']}")
        print(f"  Дата народження: {user['birth_date']}")
        print(f"  Підписка: {user['subscription_active']} ({user['subscription_type']})")
        print(f"  До: {user['subscription_until']}")
        print()
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())

