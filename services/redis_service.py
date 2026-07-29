import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)

def get_cached_response(key):
    try:
        return redis_client.get(key)
    except Exception:
        return None

def normalize_key(message: str) -> str:
    return message.strip().lower()

def cache_response(key, value):
    redis_client.set(key, value,ex=3600)