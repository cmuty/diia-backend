"""
Database migration script - Add photo_path column
"""
import sqlite3
import os

db_path = "database/diia.db"

if not os.path.exists(db_path):
    print("Database doesn't exist yet, no migration needed")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if photo_path column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'photo_path' not in columns:
        print("Adding photo_path column...")
        cursor.execute("ALTER TABLE users ADD COLUMN photo_path TEXT")
        
        # If there's old photo_url data, we could migrate it here
        # For now, just commit the new column
        
        conn.commit()
        print("✅ Migration complete! photo_path column added")
    else:
        print("✅ photo_path column already exists, no migration needed")
        
except Exception as e:
    print(f"❌ Migration error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nYou can now start the bot!")

