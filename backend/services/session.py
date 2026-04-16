from typing import Dict, Any, Optional
import time

class SessionService:
    def __init__(self, ttl: int = 1800):  # 30 minutes TTL
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "language": "en-US",
                "last_course": None,
                "last_intent": None,
                "timestamp": time.time()
            }
        return self.sessions[session_id]

    async def get_context(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        session["timestamp"] = time.time()  # Refresh TTL
        return session

    async def update_context(self, session_id: str, **kwargs):
        session = self._get_session(session_id)
        for key, value in kwargs.items():
            session[key] = value
        session["timestamp"] = time.time()

    async def clear_old_sessions(self):
        now = time.time()
        expired = [sid for sid, data in self.sessions.items() if now - data["timestamp"] > self.ttl]
        for sid in expired:
            del self.sessions[sid]

# Global singleton
session_service = SessionService()
