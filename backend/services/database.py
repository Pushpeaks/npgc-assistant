import os
import asyncio
import aiomysql
import ssl
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "collegemanagementsoftware")

class Database:
    pool: aiomysql.Pool = None

    async def connect(self):
        """Establish MySQL connection pool"""
        print(f"Connecting to MySQL: {MYSQL_HOST}:{MYSQL_PORT} as {MYSQL_USER}...")
        try:
            ssl_context = None
            if MYSQL_HOST != "localhost":
                print(f"Enabling SSL for remote MySQL connection to {MYSQL_HOST}...")
                # Create a default SSL context for secure connections
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            self.pool = await aiomysql.create_pool(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                db=MYSQL_DB,
                autocommit=True,
                charset='utf8mb4',
                cursorclass=aiomysql.DictCursor,
                ssl=ssl_context
            )
            print(f"✅ Successfully Connected to MySQL Database: {MYSQL_DB}")
        except Exception as e:
            print(f"❌ MySQL Connection Failure!")
            print(f"   Error: {e}")
            print(f"   Host: {MYSQL_HOST}, Port: {MYSQL_PORT}, User: {MYSQL_USER}")
            print(f"   Tip: If on Hugging Face, ensure Aiven IP whitelist allows 0.0.0.0/0.")
            self.pool = None

    async def close(self):
        """Close connection pool"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def fetch_all(self, query: str, params: tuple = None):
        if not self.pool: 
            print("DB Error: Connection pool not initialized")
            return []
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    return await cur.fetchall()
        except Exception as e:
            print(f"Database FetchAll Error: {e} | Query: {query[:50]}...")
            return []

    async def fetch_one(self, query: str, params: tuple = None):
        if not self.pool:
            print("DB Error: Connection pool not initialized")
            return None
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    return await cur.fetchone()
        except Exception as e:
            print(f"Database FetchOne Error: {e} | Query: {query[:50]}...")
            return None

    async def execute(self, query: str, params: tuple = None):
        if not self.pool:
            print("DB Error: Connection pool not initialized")
            return False
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    await conn.commit()
                    return True
        except Exception as e:
            print(f"Database Execute Error: {e} | Query: {query[:50]}...")
            return False

db = Database()
