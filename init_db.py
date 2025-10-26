"""
Initialize PostgreSQL database tables
Run this script after deploying to Render for the first time
"""
import asyncio
import os
from dotenv import load_dotenv
from database.models import Database

load_dotenv()


async def main():
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ DATABASE_URL not found in environment variables")
        print("Make sure .env file exists with DATABASE_URL")
        return
    
    print(f"📊 Initializing database...")
    print(f"🔗 URL: {db_url[:30]}...") # Show only first 30 chars for security
    
    db = Database(db_url)
    
    try:
        await db.init_db()
        print("\n✅ Database initialized successfully!")
        
        # Check if it's PostgreSQL
        if db.is_postgres:
            print("📊 PostgreSQL detected")
            await db.connect()
            
            # Get table count
            async with db.pool.acquire() as conn:
                tables = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                print(f"📋 Found {len(tables)} tables:")
                for table in tables:
                    print(f"   - {table['table_name']}")
        else:
            print("📊 SQLite detected")
        
        # Close connection
        await db.close()
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

