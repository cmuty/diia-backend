"""
Test login locally
"""
import asyncio
import os
from dotenv import load_dotenv
from database.models import Database

load_dotenv()

async def test_login(login: str, password: str):
    db_url = os.getenv("DATABASE_URL", "database/diia.db")
    print(f"🔌 Connecting to: {db_url[:50]}...")
    
    db = Database(db_url)
    await db.init_db()
    
    print(f"\n🔍 Trying to login with: {login} / {password}")
    
    # Get user by login
    user = await db.get_user_by_login(login)
    
    if not user:
        print(f"❌ User not found: {login}")
        return
    
    print(f"✅ User found:")
    print(f"  ID: {user['id']}")
    print(f"  Login: {user['login']}")
    print(f"  Full name: {user['full_name']}")
    print(f"  Password hash (first 20 chars): {user['password_hash'][:20]}...")
    
    # Verify password
    password_valid = await db.verify_password(user['password_hash'], password)
    
    if password_valid:
        print(f"\n✅ Password is CORRECT!")
    else:
        print(f"\n❌ Password is INCORRECT!")
    
    await db.close()

if __name__ == "__main__":
    import sys
    print("=" * 60)
    
    if len(sys.argv) >= 3:
        login = sys.argv[1]
        password = sys.argv[2]
    else:
        login = input("Enter login: ").strip()
        password = input("Enter password: ").strip()
    
    asyncio.run(test_login(login, password))

