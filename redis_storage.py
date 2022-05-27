import redis

_client = None

def get_redis_client():
    global _client
    if _client is None:
        _client = redis.Redis(unix_socket_path='./redis/docker/redis.sock')
    return _client
