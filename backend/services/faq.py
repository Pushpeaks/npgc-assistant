import os
import httpx
import asyncio
import numpy as np
import json
from typing import Optional
from dotenv import load_dotenv, find_dotenv
from services.cache import cached
from services.database import db
from utils.resilience import db_breaker, apply_breaker

load_dotenv(find_dotenv())

# Gemini Configuration
GEN_API_KEY = os.getenv("GEMINI_API_KEY")

class FAQService:
    def __init__(self, embedding_model: str = 'gemini-embedding-001', threshold: float = 0.75):
        self.embedding_model = embedding_model
        self.threshold = threshold
        
        self.faq_entries = []
        self.question_embeddings = None

    async def get_embedding(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
        """Get embedding via REST API to avoid SDK hangs."""
        if not GEN_API_KEY:
            return np.zeros(3072)
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:embedContent?key={GEN_API_KEY}"
        payload = {
            "model": f"models/{self.embedding_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    return np.array(res.json()["embedding"]["values"])
        except Exception as e:
            print(f"Embedding failed: {e}")
        return np.zeros(3072)

    @apply_breaker(db_breaker)
    async def sync_faqs(self):
        """Fetch FAQs from MySQL and prepare for similarity search"""
        if not db.pool or not GEN_API_KEY: return

        try:
            self.faq_entries = await db.fetch_all("SELECT * FROM faqs")
            
            if self.faq_entries:
                processed_embeddings = []
                valid_entries = []
                for entry in self.faq_entries:
                    emb = entry.get("embedding")
                    if isinstance(emb, str):
                        emb = json.loads(emb)
                    
                    if emb:
                        entry["embedding"] = emb
                        valid_entries.append(entry)
                        processed_embeddings.append(emb)
                
                self.faq_entries = valid_entries
                
                if processed_embeddings:
                    self.question_embeddings = np.array(processed_embeddings, dtype=np.float64)
                    # Normalize for dot product similarity
                    norm = np.linalg.norm(self.question_embeddings, axis=1, keepdims=True)
                    self.question_embeddings = np.divide(
                        self.question_embeddings, 
                        norm, 
                        out=np.zeros_like(self.question_embeddings, dtype=np.float64), 
                        where=norm!=0
                    )

            print(f"Synced {len(self.faq_entries)} FAQs from MySQL Database.")
        except Exception as e:
            print(f"Error syncing FAQs from MySQL: {e}")

    async def keyword_lookup(self, query: str) -> Optional[str]:
        """Direct SQL keyword search in FAQs - works without embeddings."""
        if not db.pool: return None
        try:
            q = query.lower()
            # Map common topics to FAQ question keywords
            topic_map = [
                (["library", "rule", "reading room", "book"], "library"),
                (["hostel", "accommodation", "dormitory", "stay"], "hostel"),
                (["placement", "career", "job", "recruit"], "placement"),
                (["admission process", "kaise apply", "how to apply", "apply online"], "admission process"),
                (["location", "address", "where is", "kahan hai", "kahan", "pata"], "located"),
                (["contact", "phone", "email", "helpline", "number"], "contact"),
                (["faculty of arts", "arts faculty", "arts department"], "Faculty of Arts"),
                (["faculty of commerce", "commerce faculty"], "Faculty of Commerce"),
                (["faculty of science", "science faculty"], "Faculty Of Science"),
                (["alumni", "notable", "old student", "purana student"], "Alumni"),
                (["courses offered", "available courses", "sabhi courses", "kya course hain"], "Courses Offered"),
                (["techfest", "events", "computer event", "fest"], "Events By Department"),
            ]
            for keywords, search_term in topic_map:
                if any(kw in q for kw in keywords):
                    result = await db.fetch_one(
                        "SELECT answer FROM faqs WHERE LOWER(question) LIKE %s LIMIT 1",
                        (f"%{search_term.lower()}%",)
                    )
                    if result and result['answer']:
                        return result['answer']
        except Exception as e:
            print(f"Keyword FAQ lookup error: {e}")
        return None

    @cached(ttl=86400, key_prefix="faq")
    async def get_answer(self, query: str) -> Optional[str]:
        """Perform semantic search using Cloud Embeddings, with keyword fallback."""
        # First try direct keyword lookup (no API needed)
        kw_result = await self.keyword_lookup(query)
        if kw_result:
            return kw_result

        if not GEN_API_KEY: return None

        try:
            if not self.faq_entries:
                await self.sync_faqs()
            
            if not self.faq_entries or self.question_embeddings is None:
                return None

            query_vec = await self.get_embedding(query, task_type="RETRIEVAL_QUERY")
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
            else:
                return None

            if self.question_embeddings.shape[1] != query_vec.shape[0]:
                print(f"FAQ Alignment Skip: DB({self.question_embeddings.shape[1]}) != Live({query_vec.shape[0]})")
                return None

            similarities = np.dot(self.question_embeddings, query_vec.T).flatten()
            best_idx = np.argmax(similarities)
            
            if similarities[best_idx] >= self.threshold:
                return self.faq_entries[best_idx]["answer"]
        
        except Exception as e:
            print(f"FAQ Search Exception: {e}")
            
        return None

    @apply_breaker(db_breaker)
    async def save_resolved_query(self, query: str, answer: str):
        """Save a new resolution to MySQL with Cloud Embeddings"""
        if not db.pool or not GEN_API_KEY: return
        
        # GUARD: Never save error messages, failures, or empty answers back to the DB
        error_markers = ["cloud brain", "api returned", "trouble reaching", "__AI_FAILURE__", "high volume", "high traffic", "try again"]
        if not answer or len(answer) < 30 or any(m in answer.lower() for m in error_markers):
            return
        
        try:
            embedding = await self.get_embedding(query)
            embedding_json = json.dumps(embedding.tolist())
            
            sql = """
                INSERT INTO faqs (question, answer, embedding, is_learned, category)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                answer = VALUES(answer), 
                embedding = VALUES(embedding), 
                is_learned = VALUES(is_learned)
            """
            await db.execute(sql, (query, answer, embedding_json, True, "Academic"))
            await self.sync_faqs()
            
        except Exception as e:
            print(f"Error saving resolved query to MySQL: {e}")

# Global singleton
faq_service = FAQService()
