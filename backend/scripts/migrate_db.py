import asyncio
import sys
import os

# Add the backend directory to sys.path so we can import services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.database import db

async def migrate():
    print("Starting database migration...")
    await db.connect()
    
    try:
        # Check if columns already exist
        cols = await db.fetch_all("DESCRIBE chatbotknowledge")
        col_names = [c['Field'] for c in cols]
        
        if 'FixedResponseEn' not in col_names:
            print("Adding FixedResponseEn column...")
            await db.execute("ALTER TABLE chatbotknowledge ADD COLUMN FixedResponseEn TEXT")
        else:
            print("FixedResponseEn column already exists.")
            
        if 'FixedResponseHi' not in col_names:
            print("Adding FixedResponseHi column...")
            await db.execute("ALTER TABLE chatbotknowledge ADD COLUMN FixedResponseHi TEXT")
        else:
            print("FixedResponseHi column already exists.")
            
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
