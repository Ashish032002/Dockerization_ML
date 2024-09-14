import redis

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_results(key, value):
    """Store the result in the Redis cache"""
    redis_client.set(key, value)

def get_cached_result(key):
    """Retrieve cached result from Redis"""
    cached_result = redis_client.get(key)
    if cached_result:
        return cached_result.decode('utf-8')
    return None
