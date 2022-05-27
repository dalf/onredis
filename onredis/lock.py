import copy

from .fields.dictionary_field import DictionaryField
from .client import get_redis_client


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
        local_copy = {}
        # DictionaryField
        for field_name, field in self.cls.__fields__.items():
            if isinstance(field, DictionaryField):
                value = getattr(self.instance, field_name)
                local_copy[field.key] = copy.deepcopy(value)
        # other field types
        keys = [v.key for v in self.cls.__fields__.values()]
        values = get_redis_client().mget(keys)
        local_copy.update({
            field.key: field.default_value if raw is None else field.deserialize(raw)
            for raw, field in zip(values, self.cls.__fields__.values())
            if not isinstance(field, DictionaryField)
        })
        # after the following line, the fields returns the value of local_copy
        self.instance._local_copy = local_copy

        del local_copy

    def write_local_copy(self):
        local_copy = self.instance._local_copy
        self.instance._local_copy = False

        # let DictionaryField write the data
        for field_name, field in self.cls.__fields__.items():
            if isinstance(field, DictionaryField):
                setattr(self.instance, field_name, local_copy[field.key])

        # use one MSET for the other fields
        serialized_values = {
            field.key: field.serialize(local_copy[field.key])
            for field in self.cls.__fields__.values()
            if not isinstance(field, DictionaryField)
        }
        get_redis_client().mset(serialized_values)

        del local_copy

    def __enter__(self):
        # acquire the lock
        result = self.lock.acquire()

        if self.local_copy:
            self.create_local_copy()

        return result

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.local_copy:
            # FIXME : an exception here keep the lock
            self.write_local_copy()
        return self.lock.release()
