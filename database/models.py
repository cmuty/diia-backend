"""
Database models and operations
"""
import aiosqlite
import bcrypt
from datetime import datetime
from typing import Optional, Dict, Any
import json


class Database:
    def __init__(self, db_path: str = "database/diia.db"):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    photo_path TEXT,
                    login TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    subscription_active BOOLEAN DEFAULT 0,
                    subscription_type TEXT DEFAULT 'безкоштовна',
                    subscription_until TEXT,
                    last_login TEXT,
                    registered_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    device_info TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS registration_temp (
                    telegram_id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_telegram_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    reply TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.commit()

    async def create_user(self, telegram_id: int, username: Optional[str], 
                         full_name: str, birth_date: str, photo_path: str,
                         login: str, password: str) -> Optional[int]:
        """Create new user"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        now = datetime.now().isoformat()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO users (
                        telegram_id, username, full_name, birth_date, 
                        photo_path, login, password_hash, registered_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, username, full_name, birth_date, 
                      photo_path, login, password_hash, now, now))
                await db.commit()
                return cursor.lastrowid
        except aiosqlite.IntegrityError:
            return None

    async def get_user_by_login(self, login: str) -> Optional[Dict[str, Any]]:
        """Get user by login"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE login = ?", (login,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def verify_password(self, login: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user password and return user data"""
        user = await self.get_user_by_login(login)
        if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            # Update last login
            await self.update_last_login(user['id'])
            return user
        return None

    async def update_last_login(self, user_id: int):
        """Update user's last login time"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, user_id)
            )
            await db.commit()

    async def update_subscription(self, user_id: int, active: bool, 
                                 sub_type: str, until: Optional[str] = None):
        """Update user subscription"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE users 
                SET subscription_active = ?, subscription_type = ?, 
                    subscription_until = ?, updated_at = ?
                WHERE id = ?
            """, (active, sub_type, until, datetime.now().isoformat(), user_id))
            await db.commit()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def login_exists(self, login: str) -> bool:
        """Check if login already exists"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM users WHERE login = ?", (login,)
            ) as cursor:
                count = await cursor.fetchone()
                return count[0] > 0

    async def save_registration_state(self, telegram_id: int, state: str, data: Dict[str, Any]):
        """Save temporary registration state"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO registration_temp (telegram_id, state, data, created_at)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, state, json.dumps(data, ensure_ascii=False), datetime.now().isoformat()))
            await db.commit()

    async def get_registration_state(self, telegram_id: int) -> Optional[tuple]:
        """Get temporary registration state"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT state, data FROM registration_temp WHERE telegram_id = ?",
                (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row[0], json.loads(row[1]) if row[1] else {}
        return None, {}

    async def clear_registration_state(self, telegram_id: int):
        """Clear temporary registration state"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM registration_temp WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    async def get_all_users(self) -> list:
        """Get all users for admin panel"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users ORDER BY registered_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_user(self, telegram_id: int, full_name: str, birth_date: str, 
                         photo_path: str, login: str, password: str) -> bool:
        """Update existing user info"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        now = datetime.now().isoformat()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users 
                    SET full_name = ?, birth_date = ?, photo_path = ?, 
                        login = ?, password_hash = ?, updated_at = ?
                    WHERE telegram_id = ?
                """, (full_name, birth_date, photo_path, login, password_hash, now, telegram_id))
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False
    
    # Ticket management methods
    async def create_ticket(self, user_id: int, user_telegram_id: int, 
                           message: str, status: str = "open") -> int:
        """Create new ticket"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO tickets (user_id, user_telegram_id, message, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, user_telegram_id, message, status, now, now))
            await db.commit()
            return cursor.lastrowid
    
    async def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        """Get ticket by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None
    
    async def update_ticket_status(self, ticket_id: int, status: str):
        """Update ticket status"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, ticket_id)
            )
            await db.commit()
    
    async def add_ticket_reply(self, ticket_id: int, reply: str):
        """Add reply to ticket"""
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tickets SET reply = ?, updated_at = ? WHERE id = ?",
                (reply, now, ticket_id)
            )
            await db.commit()
    
    async def get_open_tickets(self) -> list:
        """Get all open tickets"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tickets WHERE status IN ('open', 'answering') ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]