import threading
import redis
from typing import Dict, Optional


REDIS_CLIENT: Optional[redis.Redis] = None
LOCAL: Dict[int, redis.Redis] = {}


def set_redis_client(redis_client):
    global REDIS_CLIENT
    REDIS_CLIENT = redis_client


def get_redis_client() -> redis.Redis:
    return LOCAL.get(threading.get_ident(), REDIS_CLIENT)


def set_redis_client_for_thread(client: redis.Redis):
    if client:
        LOCAL[threading.get_ident()] = client
    else:
        del LOCAL[threading.get_ident()]
