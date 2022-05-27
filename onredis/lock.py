from onredis.dictionary_field import DictionaryField
from redis_storage import get_redis_client


class OnRedisLock:

    def __init__(self, instance, cls, lock, local_copy):
        """
        Manage the Redis lock.

        If local_copy is True, a copy of the fields is done localy.
        As long the lock is acquired all changes becomes local (whatever the thread).
        All the changes are written when the lock is released.

        If local_copy is False, the change are written to Redis directly.
        """
        self.instance = instance
        self.cls = cls
        self.lock = lock
        self.local_copy = local_copy
    
    def create_local_copy(self):
        keys = [
            v.key
            for v in self.cls.__fields__.values()
        ]
        values = get_redis_client().mget(keys)
        self.instance._local_copy = {
            v.key: v.default_value if raw is None else v.deserialize(raw)
            for raw, (k, v) in zip(values, self.cls.__fields__.items())
        }

    def write_local_copy(self):
        serialized_values = {
            v.key: v.serialize(self.instance._local_copy[v.key])
            for k, v in self.cls.__fields__.items()
            if not isinstance(v, DictionaryField)
        }
        get_redis_client().mset(serialized_values)
        self.instance._local_copy = False

    def __enter__(self):
        # acquire the lock
        result = self.lock.acquire()

        if self.local_copy:
            self.create_local_copy()

        return result
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.local_copy:
            self.write_local_copy()

        # release the lock
        return self.lock.release()
