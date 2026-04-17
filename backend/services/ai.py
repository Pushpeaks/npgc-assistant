import os
import httpx
import asyncio
from dotenv import load_dotenv, find_dotenv
from typing import List
from services.cache import cached

load_dotenv(find_dotenv())

# API Configurations
GEN_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NPGC_SYSTEM_PROMPT = """
You are NPGC Assistant, a professional and precise female AI assistant for National Post Graduate College (NPGC), Lucknow.
Your goal is to provide accurate information based STRICTLY on the provided context.

STRICT RULES:
1. Give short and precise answers (max 3-4 sentences). 
2. Use ONLY the provided context. Do NOT hallucinate or use external knowledge.
3. For lists of Faculty, Courses, or Alumni, provide a HIGH-LEVEL SUMMARY. Do not output more than 5 items unless specifically asked for a full list.
4. If the answer is not in the context, say exactly: "I apologize, but I don't have that specific information in my records. Please contact the college office at support@npgc.in or call 0522 4021304 for further assistance."
5. Always be polite and formal.
6. When speaking in Hindi, you MUST use a feminine persona and appropriate feminine grammar/maatrayein (e.g., use "कर सकती हूँ" instead of "कर सकता हूँ").
7. **DEVANAGARI ONLY**: When speaking Hindi, use ONLY Devanagari script. Do not use Hinglish or Latin characters for Hindi words.

""".strip()

class AIService:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        # Use v1beta for better compatibility with 2.5-flash
        self.api_url_base = "https://generativelanguage.googleapis.com/v1beta/models"
        self.api_url = f"{self.api_url_base}/{self.model_name}:generateContent"


    async def detect_language(self, query: str) -> str:
        """
        Detects if the query is in Hindi/Hinglish or English.
        Returns 'hi' or 'en'.
        """
        if not GEN_API_KEY: return "en"
        
        # Quick check for Devanagari characters (Sensing Devanagari Lipi)
        if any('\u0900' <= char <= '\u097f' for char in query):
            return "hi"
            
        # Common Devanagari markers that might be missed by simple range
        devanagari_markers = ['।', '॥', '॰']
        if any(marker in query for marker in devanagari_markers):
            return "hi"

        try:
            # Sensitive Prompt: Instructions to detect even a single Hindi word as 'hi'
            prompt = f"Detect language. If the text has even ONE Hindi/Hinglish word or Devanagari script, return 'hi'. Otherwise return 'en'. Query: '{query}'"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 5}
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.api_url}?key={GEN_API_KEY}", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    lang = data['candidates'][0]['content']['parts'][0]['text'].strip().lower()
                    return "hi" if "hi" in lang else "en"

                
                # If Gemini fails, use Groq for detection (Hinglish support)
                return await self.get_groq_language_detection(query)
        except Exception:
            return await self.get_groq_language_detection(query)

    async def get_groq_language_detection(self, query: str) -> str:
        """Fallback language detection using Groq."""
        if not GROQ_API_KEY: return "en"
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{
                    "role": "user", 
                    "content": f"Does this text contain any Hindi/Hinglish (Hindi in English letters)? Answer ONLY 'hi' if yes, or 'en' if no. Text: {query}"
                }],
                "max_tokens": 5
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post("https://api.groq.com/openai/v1/chat/completions",
                    json=payload, headers={"Authorization": f"Bearer {GROQ_API_KEY}"})
                if res.status_code == 200:
                    lang = res.json()['choices'][0]['message']['content'].lower()
                    return "hi" if "hi" in lang else "en"
        except: pass
        return "en"

    async def standardize_query(self, query: str) -> str:
        """
        Translates/Standardizes Hindi, Hinglish or informal queries into clean English 
        to improve vector search accuracy.
        """
        if not GEN_API_KEY: return query
        
        try:
            prompt = f"Act as a professional college query translator. Convert the following Hindi, Hinglish, or informal question about NPGC College (National Post Graduate College, Lucknow) into a clear, standard English search query. Maintain specific names like course titles (BCA, BBA) and entities. Return ONLY the translated English text.\n\nQuery: '{query}'"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 100}
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.api_url}?key={GEN_API_KEY}", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception:
            pass
        return query


    @cached(ttl=3600, key_prefix="ai")
    async def get_response(self, query: str, context: str = "", language: str = "en-US") -> str:
        """
        Calls the Google Gemini API directly via REST to avoid SDK hangs on Python 3.14.
        """
        if not GEN_API_KEY:
            return "Gemini API Key is missing. Please add GEMINI_API_KEY to your .env file."

        try:
            # Language instruction
            is_hindi = "hi" in language.lower()
            if is_hindi:
                lang_note = "CRITICAL: YOU MUST RESPOND ONLY IN HINDI (DEVANAGARI SCRIPT). Even if the context is in English, translate it and respond in formal Hindi. Do not use English script."
            else:
                lang_note = "Respond in standard English."
            
            system_prompt = f"{NPGC_SYSTEM_PROMPT}\n\nLanguage Instruction: {lang_note}".strip()

            # Build payload - Use Compatibility Mode by injecting system prompt into contents
            full_prompt = f"TASK: {lang_note}\n\nCONTEXT:\n{context}\n\nUSER QUESTION: {query}" if context else f"TASK: {lang_note}\n\nUSER QUESTION: {query}"

            payload = {
                "contents": [
                    {
                        "parts": [{"text": full_prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "maxOutputTokens": 800,
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_url_base}/{self.model_name}:generateContent?key={GEN_API_KEY}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 429:
                    print(f"!!! QUOTA EXCEEDED (429) for {self.model_name} !!! Attempting Groq Fallback...")
                    return await self.get_groq_response(query, context, language)

                if response.status_code != 200:
                    print(f"Gemini Issue ({response.status_code}). Attempting Groq Fallback...")
                    return await self.get_groq_response(query, context, language)

                data = response.json()
                try:
                    return data['candidates'][0]['content']['parts'][0]['text']
                except (KeyError, IndexError):
                    print(f"Unexpected Gemini Format. Attempting Groq Fallback...")
                    return await self.get_groq_response(query, context, language)

        except Exception as e:
            print(f"Gemini Exception: {e}. Attempting Groq Fallback...")
            return await self.get_groq_response(query, context, language)

    async def get_groq_response(self, query: str, context: str = "", language: str = "en-US") -> str:
        """Calls Groq API (Llama 3) as a high-speed fallback."""
        if not GROQ_API_KEY:
            return "__AI_FAILURE__"

        try:
            is_hindi = "hi" in language.lower()
            lang_note = "Respond ONLY in Hindi (Devanagari script). Tone: formal college assistant." if is_hindi else "Respond in standard English."
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": f"{NPGC_SYSTEM_PROMPT}\n\nLanguage Instruction: {lang_note}"},
                    {"role": "user", "content": f"CONTEXT: {context}\n\nQUESTION: {query}" if context else query}
                ],
                "temperature": 0.0,
                "max_tokens": 800
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                else:
                    print(f"Groq API Error ({response.status_code}): {response.text[:100]}")
                    return "__AI_FAILURE__"
        except Exception as e:
            print(f"Groq Exception: {e}")
            return "__AI_FAILURE__"

    async def get_suggestions(self, query: str, response: str, intent: str = None) -> List[str]:
        """
        Generates 3 relevant follow-up questions to keep the conversation going.
        """
        if not GEN_API_KEY:
            return ["Tell me more about NPGC", "How do I apply?", "Check admission status"]

        try:
            prompt = f"""
            Based on the following conversation and intent, generate 3 professional and helpful follow-up questions a student might ask.
            Each question should be concise (max 10 words).
            Return the questions as a simple list, one per line, without any numbering or bullets.

            Original Question: '{query}'
            Current Response: '{response}'
            Detected Intent: '{intent or "General"}'
            """.strip()

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 100}
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{self.api_url}?key={GEN_API_KEY}", json=payload)
                if res.status_code == 200:
                    data = res.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    # Clean up lines
                    suggestions = [s.strip() for s in raw_text.split("\n")][:3]
                    # Fallback if empty
                    if not suggestions or len(suggestions) < 1:
                        return ["Admission process", "Fee structure", "Contact info"]
                    return suggestions
        except Exception:
            pass
        
        return ["Admission deadline", "Available courses", "Campus facilities"]

# Global singleton
ai_service = AIService()
