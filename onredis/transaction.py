import copy

from .fields.dictionary_field import DictionaryField
from .client import get_redis_client, set_redis_client_for_thread


class OnRedisTransaction:

    __slots__ = ("instance", "cls", "pipeline", "execute")

    def __init__(self, instance, cls):
        """
        Manage the Redis lock.

        If local_copy is True, a copy of the fields is done localy.
        As long the lock is acquired all changes becomes local (whatever the thread).
        All the changes are written when the lock is released.

        If local_copy is False, the change are written to Redis directly.
        """
        self.instance = instance
        self.cls = cls
        self.execute = True

    def create_local_copy(self):
        local_copy = {}
        redis_client = get_redis_client()
        redis_keys = [v.key for v in self.cls.__fields__.values()]

        # abort the incoming transaction if any of the keys are changed
        redis_client.watch(*redis_keys)

        # DictionaryField: use a Python dict (do not use the DictionnaryProxy)
        for field_name, field in self.cls.__fields__.items():
            if isinstance(field, DictionaryField):
                value = getattr(self.instance, field_name)
                local_copy[field.key] = copy.deepcopy(value)

        # other field types
        values = get_redis_client().mget(redis_keys)
        local_copy.update(
            {
                field.key: field.default_value
                if raw is None
                else field.deserialize(raw)
                for raw, field in zip(values, self.cls.__fields__.values())
                if not isinstance(field, DictionaryField)
            }
        )

        # after the following line, the fields returns the value of local_copy
        self.instance._local_copy = local_copy

        # start a Redis transaction
        redis_client.multi()

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
        set_redis_client_for_thread(get_redis_client().pipeline())
        self.create_local_copy()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pipeline = get_redis_client()
        try:
            if self.execute and exc_type is None:
                # the transaction was aborted and there is no exception
                self.write_local_copy()
                pipeline.execute()
            else:
                # the transaction was aborted OR there is an exception
                self.instance._local_copy = False
                pipeline.discard()
        finally:
            set_redis_client_for_thread(None)
            pipeline.reset()

    def discard(self):
        self.execute = False
