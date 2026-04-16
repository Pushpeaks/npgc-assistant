from aiobreaker import CircuitBreaker
import asyncio
from datetime import timedelta

# Circuit Breaker for Databases/services
# Parameters: fail_max (failed attempts), timeout_duration (seconds to stay open)
db_breaker = CircuitBreaker(fail_max=5, timeout_duration=timedelta(seconds=60))

async def fallback_empty_list():
    return []

async def fallback_string():
    return "I'm currently experiencing high traffic, but I can still answer specific questions about NPGC Admissions, Courses, and Contact details! Please try asking a specific question."


async def fallback_none():
    return None

def apply_breaker(breaker: CircuitBreaker, fallback=None):
    """
    Decorator to apply circuit breaker with optional fallback handling.
    """
    def decorator(func):
        wrapped = breaker(func)
        
        async def wrapper(*args, **kwargs):
            try:
                return await wrapped(*args, **kwargs)
            except Exception as e:
                print(f"Breaker caught error in {func.__name__}: {e}")
                if fallback:
                    return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
                raise e
        return wrapper
    return decorator
