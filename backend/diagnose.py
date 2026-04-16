import asyncio, sys
sys.path.insert(0, '.')
from services.database import db
from services.knowledge import knowledge_service

async def diagnose():
    await db.connect()
    
    # 1. Show all tables
    tables = await db.fetch_all("SHOW TABLES")
    print("=== TABLES ===")
    for t in tables:
        print(list(t.values())[0])
    
    for tbl in ["chatbotknowledge", "faqs", "course"]:
        try:
            cnt = await db.fetch_all(f"SELECT COUNT(*) as c FROM {tbl}")
            print(f"\n{tbl}: {cnt[0]['c']} rows")
        except Exception as e:
            print(f"\n{tbl}: ERROR - {e}")

    # 4. Sample context_string
    sample = await db.fetch_all(
        "SELECT intent, SUBSTRING(FixedResponseEn, 1, 300) as ctx "
        "FROM chatbotknowledge WHERE intent='LIBRARY_INFRA' LIMIT 1"
    )
    print("\n=== SAMPLE CONTEXT (LIBRARY_INFRA) ===")
    for s in sample:
        print(s)
    
    # 5. Test intent matching
    await knowledge_service.sync_intents()
    print(f"\n=== INTENT ENTRIES LOADED: {len(knowledge_service.intent_entries)} ===")
    
    # Test a few queries
    queries = ["rules for the library", "admission process", "what courses are available"]
    for q in queries:
        r = await knowledge_service.get_intent_data(q)
        if r:
            print(f"'{q}' -> MATCHED: {r.get('intent')} | ctx_len={len(r.get('context_string',''))}")
        else:
            print(f"'{q}' -> NO MATCH")
    
    await db.close()

asyncio.run(diagnose())
