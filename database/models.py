"""
Database models with PostgreSQL support
Supports both SQLite (local) and PostgreSQL (production)
"""
import os
import ssl
import bcrypt
import asyncpg
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Any, List
import json
from urllib.parse import urlparse


class Database:
    def __init__(self, db_url: str = None):
        """
        Initialize database connection
        db_url can be:
        - PostgreSQL: postgresql://user:pass@host/db
        - SQLite: sqlite:///path/to/db.db or just path/to/db.db
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "database/diia.db")
        self.is_postgres = self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")
        print(f"📊 Database URL: {self.db_url[:50]}... (PostgreSQL: {self.is_postgres})")
        
        if not self.is_postgres:
            # SQLite path
            if self.db_url.startswith("sqlite:///"):
                self.db_path = self.db_url.replace("sqlite:///", "")
            else:
                self.db_path = self.db_url
            self.pool = None
        else:
            # PostgreSQL connection pool
            self.pool = None
            self.db_path = None  # Not used for PostgreSQL

    async def connect(self):
        """Create connection pool for PostgreSQL"""
        if self.is_postgres:
            if self.pool:
                print(f"✅ Connection pool already exists, reusing...")
                return
            
            try:
                print(f"🔌 Connecting to PostgreSQL...")
                
                # Парсим URL для извлечения параметров
                parsed = urlparse(self.db_url)
                host = parsed.hostname
                port = parsed.port or 5432
                user = parsed.username
                password = parsed.password
                database = parsed.path.lstrip('/')
                
                if not all([host, user, password, database]):
                    raise ValueError(f"Missing required database parameters. Host: {host}, User: {user}, Database: {database}")
                
                print(f"🔌 Подключение к PostgreSQL: {user}@{host}:{port}/{database}")
                
                # Проверяем переменную окружения для SSL
                ssl_mode = os.getenv("POSTGRES_SSL", "require")
                
                # Настраиваем SSL для Render.com
                ssl_config = None
                if ssl_mode.lower() != "disable" and ssl_mode.lower() != "false":
                    # Создаем SSL контекст для Render.com
                    # Render.com требует SSL, но не требует проверки сертификата
                    ssl_config = ssl.create_default_context()
                    ssl_config.check_hostname = False
                    ssl_config.verify_mode = ssl.CERT_NONE
                    print("🔒 Используется SSL соединение")
                else:
                    print("⚠️ SSL отключен")
                
                print(f"🔄 Creating connection pool (this may take a few seconds)...")
                # Создаем пул с явными параметрами и SSL
                self.pool = await asyncpg.create_pool(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=database,
                    min_size=1,
                    max_size=10,
                    ssl=ssl_config,
                    command_timeout=60,  # Таймаут для команд
                    server_settings={
                        'connect_timeout': '10',  # Таймаут подключения 10 секунд
                    }
                )
                print(f"✅ PostgreSQL connection pool created successfully")
            except Exception as e:
                print(f"❌ Failed to connect to PostgreSQL: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                raise
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def init_db(self):
        """Initialize database tables"""
        if self.is_postgres:
            await self._init_postgres()
        else:
            await self._init_sqlite()
    
    async def _init_postgres(self):
        """Initialize PostgreSQL tables"""
        await self.connect()
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    full_name TEXT NOT NULL,
                    birth_date TEXT NOT NULL,
                    photo_path TEXT,
                    login TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    subscription_active BOOLEAN DEFAULT FALSE,
                    subscription_type TEXT DEFAULT 'безкоштовна',
                    subscription_until TIMESTAMP,
                    last_login TIMESTAMP,
                    registered_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """)
            
            # Sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    device_info TEXT,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Registration temp table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS registration_temp (
                    telegram_id BIGINT PRIMARY KEY,
                    state TEXT NOT NULL,
                    data JSONB,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            
            # Payments table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    currency TEXT NOT NULL,
                    payment_method TEXT,
                    status TEXT NOT NULL,
                    subscription_type TEXT NOT NULL,
                    subscription_days INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            print("✅ PostgreSQL tables initialized")
    
    async def _init_sqlite(self):
        """Initialize SQLite tables"""
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
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    payment_method TEXT,
                    status TEXT NOT NULL,
                    subscription_type TEXT NOT NULL,
                    subscription_days INTEGER,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.commit()
            print("✅ SQLite tables initialized")

    # User operations
    async def create_user(self, telegram_id: int, username: Optional[str],
                         full_name: str, birth_date: str, photo_path: str,
                         login: str, password: str) -> Optional[int]:
        """Create new user"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                row = await conn.fetchrow("""
                    INSERT INTO users (telegram_id, username, full_name, birth_date, photo_path,
                                     login, password_hash, registered_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                """, telegram_id, username, full_name, birth_date, photo_path,
                    login, password_hash, now, now)
                return row['id'] if row else None
        else:
            now = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO users (telegram_id, username, full_name, birth_date, photo_path,
                                     login, password_hash, registered_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (telegram_id, username, full_name, birth_date, photo_path,
                     login, password_hash, now, now))
                await db.commit()
                return cursor.lastrowid

    async def get_user_by_login(self, login: str) -> Optional[Dict[str, Any]]:
        """Get user by login"""
        try:
            print(f"🔍 get_user_by_login: searching for login='{login}'")
            if self.is_postgres:
                print(f"📊 PostgreSQL mode, connecting...")
                await self.connect()
                if not self.pool:
                    print(f"❌ Connection pool is None!")
                    raise RuntimeError("PostgreSQL connection pool not initialized")
                print(f"✅ Connection pool ready, acquiring connection...")
                async with self.pool.acquire() as conn:
                    print(f"✅ Connection acquired, executing query...")
                    row = await conn.fetchrow("SELECT * FROM users WHERE login = $1", login)
                    print(f"✅ Query executed, result: {'found' if row else 'not found'}")
                    return dict(row) if row else None
            else:
                print(f"📁 SQLite mode")
                async with aiosqlite.connect(self.db_path) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT * FROM users WHERE login = ?", (login,)) as cursor:
                        row = await cursor.fetchone()
                        return dict(row) if row else None
        except Exception as e:
            print(f"❌ Error in get_user_by_login: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram ID"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                return dict(row) if row else None
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    async def update_user(self, telegram_id: int, full_name: str, birth_date: str,
                         photo_path: str, login: str, password: str) -> bool:
        """Update user information"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                result = await conn.execute("""
                    UPDATE users 
                    SET full_name = $1, birth_date = $2, photo_path = $3,
                        login = $4, password_hash = $5, updated_at = $6
                    WHERE telegram_id = $7
                """, full_name, birth_date, photo_path, login, password_hash, now, telegram_id)
                return result != "UPDATE 0"
        else:
            now = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users 
                    SET full_name = ?, birth_date = ?, photo_path = ?,
                        login = ?, password_hash = ?, updated_at = ?
                    WHERE telegram_id = ?
                """, (full_name, birth_date, photo_path, login, password_hash, now, telegram_id))
                await db.commit()
                return True

    async def update_last_login(self, user_id: int):
        """Update last login timestamp"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                await conn.execute("UPDATE users SET last_login = $1 WHERE id = $2", now, user_id)
        else:
            now = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))
                await db.commit()

    async def update_subscription(self, user_id: int, active: bool, 
                                 sub_type: str, until: Optional[datetime] = None):
        """Update user subscription"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                await conn.execute("""
                    UPDATE users 
                    SET subscription_active = $1, subscription_type = $2, 
                        subscription_until = $3, updated_at = $4
                    WHERE id = $5
                """, active, sub_type, until, now, user_id)
        else:
            now = datetime.now().isoformat()  # string for SQLite
            until_str = until.isoformat() if until else None  # convert datetime to string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users 
                    SET subscription_active = ?, subscription_type = ?, 
                        subscription_until = ?, updated_at = ?
                    WHERE id = ?
                    """, (active, sub_type, until_str, now, user_id))
                await db.commit()

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM users ORDER BY id DESC")
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users ORDER BY id DESC") as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]

    # Registration temp operations
    async def save_registration_state(self, telegram_id: int, state: str, data: dict):
        """Save registration state"""
        data_json = json.dumps(data)
        
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                await conn.execute("""
                    INSERT INTO registration_temp (telegram_id, state, data, created_at)
                    VALUES ($1, $2, $3::jsonb, $4)
                    ON CONFLICT (telegram_id) DO UPDATE 
                    SET state = $2, data = $3::jsonb, created_at = $4
                """, telegram_id, state, data_json, now)
        else:
            now_str = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO registration_temp (telegram_id, state, data, created_at)
                    VALUES (?, ?, ?, ?)
                    """, (telegram_id, state, data_json, now_str))
                await db.commit()

    async def get_registration_state(self, telegram_id: int):
        """Get registration state"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT state, data FROM registration_temp WHERE telegram_id = $1",
                    telegram_id
                )
                if row:
                    return row['state'], json.loads(row['data']) if row['data'] else {}
                return None, {}
        else:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT state, data FROM registration_temp WHERE telegram_id = ?",
                    (telegram_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return row['state'], json.loads(row['data']) if row['data'] else {}
                    return None, {}

    async def delete_registration_state(self, telegram_id: int):
        """Delete registration state"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                await conn.execute("DELETE FROM registration_temp WHERE telegram_id = $1", telegram_id)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM registration_temp WHERE telegram_id = ?", (telegram_id,))
                await db.commit()

    async def clear_registration_state(self, telegram_id: int):
        """Clear registration state (alias for delete_registration_state)"""
        await self.delete_registration_state(telegram_id)

    # Payment operations
    async def create_payment(self, user_id: int, amount: float, currency: str,
                            subscription_type: str, subscription_days: int,
                            payment_method: str = None) -> int:
        """Create payment record"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                row = await conn.fetchrow("""
                    INSERT INTO payments (user_id, amount, currency, payment_method, status,
                                        subscription_type, subscription_days, created_at)
                    VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7)
                    RETURNING id
                """, user_id, amount, currency, payment_method, subscription_type, subscription_days, now)
                return row['id']
        else:
            now = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO payments (user_id, amount, currency, payment_method, status,
                                        subscription_type, subscription_days, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
                """, (user_id, amount, currency, payment_method, subscription_type, subscription_days, now))
                await db.commit()
                return cursor.lastrowid

    async def complete_payment(self, payment_id: int):
        """Mark payment as completed"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                now = datetime.now()  # datetime object for PostgreSQL
                await conn.execute("""
                    UPDATE payments 
                    SET status = 'completed', completed_at = $1 
                    WHERE id = $2
                """, now, payment_id)
        else:
            now = datetime.now().isoformat()  # string for SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE payments 
                    SET status = 'completed', completed_at = ? 
                    WHERE id = ?
                """, (now, payment_id))
                await db.commit()

    async def verify_password(self, stored_hash: str, password: str) -> bool:
        """Verify password against stored hash"""
        try:
            if not stored_hash or not password:
                print(f"❌ verify_password: stored_hash or password is empty")
                return False
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except Exception as e:
            print(f"❌ verify_password error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False

    async def login_exists(self, login: str) -> bool:
        """Check if login already exists"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT 1 FROM users WHERE login = $1", login)
                return row is not None
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM users WHERE login = ?", (login,)) as cursor:
                    row = await cursor.fetchone()
                    return row is not None

    async def telegram_id_exists(self, telegram_id: int) -> bool:
        """Check if telegram_id already exists"""
        if self.is_postgres:
            await self.connect()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("SELECT 1 FROM users WHERE telegram_id = $1", telegram_id)
                return row is not None
        else:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row is not None
