import asyncio
import sys
import os
import httpx
import json

# Add the backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from services.database import db
from services.knowledge import knowledge_service

# Load API Key directly from env or .env file
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def generate_responses_groq(intent_type, context_string):
    """Uses Groq (Llama 3.3 70B) to generate elegant English and Hindi responses."""
    if not context_string:
        return None, None
    
    # Clean context string
    context_string = str(context_string)[:4000]
    
    prompt = f"""
    You are NPGC Assistant, a professional female AI for National Post Graduate College (NPGC), Lucknow.
    Based on the following academic data, generate TWO high-quality responses:
    1. A formal English response (3-4 sentences).
    2. A formal Hindi response in DEVANAGARI script (3-4 sentences). Use a feminine professional persona (e.g., use "कर सकती हूँ").
    
    DATA:
    {context_string}
    
    Return the result STRAIGHT in JSON format with keys "en" and "hi". Do not include markdown code blocks or any other characters.
    JSON:
    """.strip()

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    api_url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            res = await client.post(api_url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                text = data['choices'][0]['message']['content'].strip()
                result = json.loads(text)
                return result.get("en"), result.get("hi")
            else:
                print(f"      [GROQ ERROR] Status {res.status_code} | Body: {res.text[:100]}")
    except Exception as e:
        print(f"      [GEN ERROR] {e}")
    return None, None

async def fetch_fallback_data(intent_type):
    """Fallback to searching FAQs by keyword if knowledge service fails."""
    # Common keywords for intents
    keywords = {
        "CAMPUS_GENERAL": "placement",
        "ADMISSION_PROCEDURE": "admission process",
        "LIBRARY_INFRA": "library",
        "HOSTEL_INFO": "hostel",
        "EVENTS_INFO": "events",
        "COLLEGE_CONTACT": "contact",
        "COLLEGE_ADDRESS": "location",
        "COLLEGE_HISTORY": "history",
        "COLLEGE_MOTTO": "motto",
        "COLLEGE_VISION": "vision",
        "COLLEGE_MISSION": "mission",
        "COLLEGE_PRINCIPAL": "principal",
        "COLLEGE_ACCREDITATION": "accreditation",
        "COLLEGE_POLICY": "policy",
        "RESEARCH_SUPPORT": "research",
        "CANTEEN_QUERY": "canteen",
    }
    kw = keywords.get(intent_type, intent_type.split('_')[0].lower())
    row = await db.fetch_one("SELECT answer FROM faqs WHERE LOWER(question) LIKE %s OR LOWER(answer) LIKE %s LIMIT 1", (f"%{kw}%", f"%{kw}%"))
    if row and row['answer']:
        return row['answer']
    return None

async def run_population():
    print("--- STARTING POPULATION V3 (GROQ) ---")
    await db.connect()
    
    # Sync intents to ensure internal state is ready
    await knowledge_service.sync_intents()
    
    intents = await db.fetch_all("SELECT Id, Intent FROM chatbotknowledge")
    print(f"Total Intents: {len(intents)}")
    
    for intent in intents:
        i_id = intent['Id']
        i_type = intent['Intent']
        
        print(f"Processing: {i_type} (ID: {i_id})")
        
        # 1. Primary data fetch
        data_res = await knowledge_service.get_intent_data_by_intent(i_type, "college")
        ctx = data_res.get("context_string") if data_res else None
        
        # 2. Fallback data fetch
        if not ctx:
            ctx = await fetch_fallback_data(i_type)
            
        if not ctx:
            print(f"   [SKIP] Still no data found")
            continue
            
        print(f"   [DATA FOUND] Context len: {len(ctx)}")
        
        # 3. Generate
        en_resp, hi_resp = await generate_responses_groq(i_type, ctx)
        
        if en_resp and hi_resp:
            sql = "UPDATE chatbotknowledge SET FixedResponseEn = %s, FixedResponseHi = %s WHERE Id = %s"
            await db.execute(sql, (en_resp, hi_resp, i_id))
            print(f"   [SUCCESS] Saved bilingual response")
        else:
            print(f"   [FAIL] Generation failed")
            
        await asyncio.sleep(0.5) # Groq is fine with high rate
        
    print("--- POPULATION V3 FINISHED ---")
    await db.close()

if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("GROQ_API_KEY missing.")
    else:
        asyncio.run(run_population())
