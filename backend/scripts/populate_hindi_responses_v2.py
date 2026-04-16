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
GEN_API_KEY = os.getenv("GEMINI_API_KEY")

async def generate_responses(intent_type, context_string):
    """Uses Gemini to generate elegant English and Hindi responses."""
    if not context_string:
        return None, None
    
    # Clean context string
    context_string = context_string[:3500]
    
    prompt = f"""
    You are NPGC Assistant, a professional female AI for National Post Graduate College (NPGC), Lucknow.
    Based on the following academic data, generate TWO high-quality responses:
    1. A formal English response (3-4 sentences).
    2. A formal Hindi response in DEVANAGARI script (3-4 sentences). Use a feminine professional persona ("कर सकती हूँ").
    
    DATA:
    {context_string}
    
    Return the result STRAIGHT in JSON format with keys "en" and "hi". Do not include markdown code blocks.
    JSON:
    """.strip()

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
    }
    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEN_API_KEY}"
    
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            res = await client.post(api_url, json=payload)
            if res.status_code == 200:
                data = res.json()
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"): text = text[4:]
                
                try:
                    result = json.loads(text)
                    return result.get("en"), result.get("hi")
                except Exception as e:
                    print(f"      [PARSE ERROR] {e} | Raw: {text[:100]}")
            else:
                print(f"      [API ERROR] Status {res.status_code} | Body: {res.text[:100]}")
    except Exception as e:
        print(f"      [GEN ERROR] {e}")
    return None, None



async def run_population():
    print("--- STARTING POPULATION ---")
    await db.connect()
    
    # Force sync knowledge service
    await knowledge_service.sync_intents()
    
    intents = await db.fetch_all("SELECT Id, Intent FROM chatbotknowledge")
    print(f"Total Intents to process: {len(intents)}")
    
    for intent in intents:
        i_id = intent['Id']
        i_type = intent['Intent']
        
        print(f"Processing: {i_type} (ID: {i_id})")
        
        # Manually trigger data fetch logic
        data_res = await knowledge_service.get_intent_data_by_intent(i_type, "college")
        if not data_res or not data_res.get("context_string"):
            print(f"   [SKIP] No data")
            continue
            
        ctx = data_res["context_string"]
        print(f"   [FETCHED] Context len: {len(ctx)}")
        
        en_resp, hi_resp = await generate_responses(i_type, ctx)
        
        if en_resp and hi_resp:
            sql = "UPDATE chatbotknowledge SET FixedResponseEn = %s, FixedResponseHi = %s WHERE Id = %s"
            await db.execute(sql, (en_resp, hi_resp, i_id))
            print(f"   [SAVED] {i_type}")
        else:
            print(f"   [FAIL] Generation failed")
            
        await asyncio.sleep(1) # Faster but still throttled
        
    print("--- FINISHED ---")
    await db.close()

if __name__ == "__main__":
    if not GEN_API_KEY:
        print("API Key missing.")
    else:
        asyncio.run(run_population())
