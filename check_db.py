import asyncio
import aiosqlite

async def check_database():
    db_path = "database/diia.db"
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        print("=== USERS IN DATABASE ===\n")
        
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            
            if not rows:
                print("❌ NO USERS FOUND!")
                return
            
            for row in rows:
                user = dict(row)
                print(f"👤 User ID: {user['id']}")
                print(f"   Login: {user['login']}")
                print(f"   Full Name: {user['full_name']}")
                print(f"   Birth Date: {user['birth_date']}")
                print(f"   Photo: {user['photo_url']}")
                print(f"   Telegram ID: {user['telegram_id']}")
                print(f"   Registered: {user['registered_at']}")
                print()

if __name__ == "__main__":
    asyncio.run(check_database())

