import redis

REDIS_CLIENT: redis.Redis = None


def set_redis_client(redis_client):
    global REDIS_CLIENT
    REDIS_CLIENT = redis_client


def get_redis_client() -> redis.Redis:
    return REDIS_CLIENT
