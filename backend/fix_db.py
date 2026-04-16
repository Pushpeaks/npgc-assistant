import asyncio, sys
sys.path.insert(0, '.')
from services.database import db

async def fix():
    await db.connect()
    
    # 1. Delete corrupted FAQ entries saved by the bot errors
    deleted = await db.execute(
        "DELETE FROM faqs WHERE answer LIKE '%cloud brain%' OR answer LIKE '%API returned%' OR answer LIKE '%trouble reaching%'"
    )
    print(f"Deleted corrupted FAQ entries: {deleted}")
    
    # 2. Check chatbotknowledge actual columns
    cols = await db.fetch_all("DESCRIBE chatbotknowledge")
    print("\nchatbotknowledge columns:")
    for c in cols:
        print(f"  {c['Field']} - {c['Type']}")
    
    # 3. Check vector column name and sample
    sample_row = await db.fetch_all("SELECT * FROM chatbotknowledge LIMIT 1")
    if sample_row:
        print("\nchatbotknowledge keys:", list(sample_row[0].keys()))
    
    # 4. Count valid vectors
    nullvec = await db.fetch_all("SELECT COUNT(*) as c FROM chatbotknowledge WHERE vector IS NULL OR vector = ''")
    allrows = await db.fetch_all("SELECT COUNT(*) as c FROM chatbotknowledge")
    print(f"\nTotal intents: {allrows[0]['c']}, Null vectors: {nullvec[0]['c']}")
    
    await db.close()

asyncio.run(fix())
