from ..client import get_redis_client
from .basic import AbstractField, GenericField


class DictionaryField(AbstractField):

    def __init__(self, key_field=None, value_field=None, default_value=None):
        self.key_field = key_field or GenericField(None)
        self.value_field = value_field or GenericField(None)
        self.default_value = default_value

    def redis_get(self, obj, objtype=None):
        # FIXME: default_value is ignored
        return DictionnaryProxy(
            obj, get_redis_client(), self.key, self.key_field, self.value_field
        )

    def redis_set(self, obj, value):
        redis_client = get_redis_client()
        redis_client.delete(self.key)
        if value:
            value = {
                self.key_field.serialize(k): self.value_field.serialize(v)
                for k, v in value.items()
            }
            redis_client.hmset(self.key, value)

    def serialize(self, value) -> bytes:
        raise NotImplemented()

    def deserialize(self, raw: bytes):
        raise NotImplemented()


class GenericDictionaryField(DictionaryField):
    def __init__(self, default_value=None):
        super().__init__(
            GenericField(None), GenericField(None), default_value=default_value
        )


class DictionnaryProxy:

    __slots__ = ("obj", "redis_client", "redis_key", "key_field", "value_field")

    def __init__(self, obj, redis_client, redis_key, key_field, value_field):
        self.obj = obj
        self.redis_client = redis_client
        self.redis_key = redis_key
        self.key_field = key_field
        self.value_field = value_field

    def _no_local_copy(self):
        if self.obj._local_copy:
            raise ValueError('A lock was acquired after this class was created')

    def __getitem__(self, key):
        self._no_local_copy()
        skey = self.key_field.serialize(key)
        return self.value_field.deserialize(
            self.redis_client.hget(self.redis_key, skey)
        )

    def __setitem__(self, key, item):
        self._no_local_copy()
        skey = self.key_field.serialize(key)
        sitem = self.value_field.serialize(item)
        self.redis_client.hset(self.redis_key, skey, sitem)

    def __delitem__(self, key):
        self._no_local_copy()
        skey = self.key_field.serialize(key)
        self.redis_client.hdel(self.redis_key, skey)

    def __contains__(self, key):
        self._no_local_copy()
        skey = self.key_field.serialize(key)
        return True if self.redis_client.hexists(self.redis_key, skey) else False

    def __len__(self):
        self._no_local_copy()
        return self.redis_client.hlen(self.redis_key)

    def __iter__(self):
        self._no_local_copy()
        raise NotImplemented()

    def __next__(self):
        self._no_local_copy()
        raise NotImplemented()

    def __deepcopy__(self, memo=None):
        self._no_local_copy()
        return {
            self.key_field.deserialize(k): self.value_field.deserialize(v)
            for k, v in self.redis_client.hgetall(self.redis_key).items()
        }

    def items(self):
        self._no_local_copy()
        return self.__deepcopy__().items()

    def values(self):
        self._no_local_copy()
        return [
            self.value_field.deserialize(v)
            for v in self.redis_client.hvals(self.redis_key)
        ]

    def keys(self):
        self._no_local_copy()
        return [
            self.key_field.deserialize(k)
            for k in self.redis_client.hkeys(self.redis_key)
        ]

    def __repr__(self):
        self._no_local_copy()
        return repr(self.__deepcopy__(None))
