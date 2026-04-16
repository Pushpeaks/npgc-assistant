import redis
import os
import functools
import orjson as json
from typing import Optional, Any, Callable
from cachetools import TTLCache
from utils.resilience import db_breaker, apply_breaker

# Configuration
REDIS_URL = os.getenv("REDIS_URL", f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/0")

# L1 Cache (Local Memory) - Top 100 queries for 10 minutes
l1_cache = TTLCache(maxsize=100, ttl=600)

class CacheService:
    def __init__(self):
        self.enabled = False
        self.redis_client = None
        
        # Clean the REDIS_URL from potential empty strings in .env
        clean_url = REDIS_URL.strip() if REDIS_URL else None
        
        if not clean_url or clean_url == "redis://localhost:6379/0":
            # If no custom URL, we check if REDIS_URL was empty or just default
            # If default but no host set, we might want to stay disabled
            if not os.getenv("REDIS_URL") and not os.getenv("REDIS_HOST"):
                print("L2 Cache (Redis) skipped: No REDIS_URL provided.")
                return

        try:
            self.redis_client = redis.from_url(
                clean_url,
                decode_responses=True,
                socket_timeout=1.0,
                socket_connect_timeout=1.0
            )
            self.redis_client.ping()
            self.enabled = True
            print("L2 Cache (Redis) Connected.")
        except Exception as e:
            print(f"L2 Cache (Redis) Unavailable: {e}")
            self.redis_client = None
            self.enabled = False

    @apply_breaker(db_breaker, fallback=None)
    def get_l2(self, key: str) -> Optional[Any]:
        if not self.enabled or not self.redis_client:
            return None
        val = self.redis_client.get(key)
        return json.loads(val) if val else None

    @apply_breaker(db_breaker)
    def set_l2(self, key: str, value: Any, expire: int = 3600):
        if not self.enabled or not self.redis_client:
            return
        self.redis_client.setex(key, expire, json.dumps(value))

# Global singleton
cache_service = CacheService()

def cached(ttl: int = 3600, key_prefix: str = "cache"):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Compute cache key
            arg_str = ":".join([str(arg) for arg in args[1:]])
            kwarg_str = ":".join([f"{k}={v}" for k, v in kwargs.items()])
            cache_key = f"{key_prefix}:{func.__name__}:{arg_str}:{kwarg_str}".strip(":")

            # L1 Check (Blazing Fast)
            if cache_key in l1_cache:
                return l1_cache[cache_key]

            # L2 Check (Network)
            if cache_service.enabled:
                cached_val = cache_service.get_l2(cache_key)
                if cached_val is not None:
                    l1_cache[cache_key] = cached_val  # Promote to L1
                    return cached_val

            # Execute
            result = await func(*args, **kwargs)
            
            # Store
            if result is not None:
                l1_cache[cache_key] = result
                if cache_service.enabled:
                    cache_service.set_l2(cache_key, result, expire=ttl)

            return result
        return wrapper
    return decorator
