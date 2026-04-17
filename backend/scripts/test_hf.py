import os
import asyncio
import httpx
from dotenv import load_dotenv

# Try to load .env if it exists (local dev), but in HF it will use environment variables
load_dotenv()

async def test_env():
    print("=== Hugging Face / Production Diagnostic Tool ===")
    
    # 1. Check API Keys
    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    
    print(f"\n[AI SERVICES]")
    print(f"GEMINI_API_KEY: {'FOUND [OK]' if gemini_key else 'MISSING [!!]'}")
    print(f"GROQ_API_KEY:   {'FOUND [OK]' if groq_key else 'MISSING [!!]'}")
    
    # 2. Check Database Details
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    db_name = os.getenv("MYSQL_DB")
    
    print(f"\n[DATABASE CONFIG]")
    print(f"Host: {host if host else 'MISSING [!!]'}")
    print(f"Port: {port if port else 'MISSING [!!]'}")
    print(f"DB:   {db_name if db_name else 'MISSING [!!]'}")
    
    # 3. Test Gemini API Connectivity
    if gemini_key:
        print(f"\n[TESTING GEMINI API]")
        model = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {"contents": [{"parts": [{"text": "Health check. Reply with 'OK'."}]}]}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    print(f"Gemini Status: Success [OK] (Response: {res.json()['candidates'][0]['content']['parts'][0]['text'].strip()})")
                elif res.status_code == 429:
                    print(f"Gemini Status: QUOTA EXCEEDED (429) [!!] - Free tiers have low limits.")
                else:
                    print(f"Gemini Status: Failed [!!] (Code: {res.status_code}, Msg: {res.text[:100]})")
        except Exception as e:
            print(f"Gemini Status: Error [!!] ({e})")
    
    # 4. Final Tip
    print("\n" + "="*40)
    print("TIP: If Database details are correct but the bot fails,")
    print("Go to Aiven Console and Whitelist IP 0.0.0.0/0 permanently.")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(test_env())
