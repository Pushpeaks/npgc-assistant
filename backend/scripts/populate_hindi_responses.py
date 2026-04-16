import asyncio
import sys
import os
import httpx
import json

# Add the backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.database import db
from services.knowledge import knowledge_service
from services.ai import ai_service

# Load API Key directly from env or .env file
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
GEN_API_KEY = os.getenv("GEMINI_API_KEY")

async def generate_responses(intent_type, context_string):
    """Uses Gemini to generate elegant English and Hindi responses."""
    if not context_string:
        return None, None
    
    # Clean context string to avoid huge prompts
    context_string = context_string[:3000]
    
    prompt = f"""
    You are NPGC Assistant, a professional female AI for National Post Graduate College, Lucknow.
    Based on the following academic data, generate TWO high-quality responses:
    1. A formal English response (3-4 sentences).
    2. A formal Hindi response in DEVANAGARI script (3-4 sentences). Use a feminine persona ("कर सकती हूँ").
    
    DATA:
    {context_string}
    
    Return the result STRAIGHT in JSON format with keys "en" and "hi". Do not include markdown code blocks or any other text.
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
                # Clean potential markdown
                if text.startswith("```json"):
                    text = text[7:-3].strip()
                elif text.startswith("```"):
                    text = text[3:-3].strip()
                
                try:
                    result = json.loads(text)
                    return result.get("en"), result.get("hi")
                except json.JSONDecodeError:
                    print(f"   ! JSON Parse Error for {intent_type}. Raw: {text[:100]}...")
            else:
                print(f"   ! API Error {res.status_code} for {intent_type}: {res.text[:100]}")
    except Exception as e:
        print(f"   ! Exception for {intent_type}: {str(e)[:100]}")
    return None, None

async def run_population():
    print("Connecting to database...")
    await db.connect()
    
    print("Fetching intents from chatbotknowledge...")
    intents = await db.fetch_all("SELECT * FROM chatbotknowledge")
    
    print(f"Processing {len(intents)} intents...")
    
    for intent in intents:
        intent_type = intent['Intent']
        print(f" - Processing intent: {intent_type}")
        
        # 1. Fetch data context using knowledge_service logic
        try:
            data_res = await knowledge_service.get_intent_data_by_intent(intent_type, "")
            if not data_res:
                # If query empty fails, try a generic query for some intents
                data_res = await knowledge_service.get_intent_data_by_intent(intent_type, "college")
                
            if not data_res:
                print(f"   ! No data found for {intent_type}")
                continue
                
            context_string = data_res.get("context_string", "")
            if not context_string:
                print(f"   ! Empty context for {intent_type}")
                continue
                
            print(f"   [Context Size: {len(context_string)} chars]")
                
            # 2. Generate bilingual responses
            en_resp, hi_resp = await generate_responses(intent_type, context_string)
            
            if en_resp and hi_resp:
                # 3. Save back to DB
                sql = "UPDATE chatbotknowledge SET FixedResponseEn = %s, FixedResponseHi = %s WHERE Id = %s"
                ok = await db.execute(sql, (en_resp, hi_resp, intent['Id']))
                if ok:
                    print(f"   [SUCCESS]")
                else:
                    print(f"   [DB SAVE FAILED]")
            else:
                print(f"   [GENERATION FAILED]")
            
            # Rate limiting
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"   ! Error processing {intent_type}: {e}")
            
    print("\nAll done!")
    await db.close()


            
    print("\nAll done!")
    await db.close()

if __name__ == "__main__":
    if not GEN_API_KEY:
        print("Error: GEMINI_API_KEY not found in environment.")
    else:
        asyncio.run(run_population())
