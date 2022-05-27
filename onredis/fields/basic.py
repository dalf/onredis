from abc import ABC, abstractmethod
import pickle
import struct

from ..client import get_redis_client


class AbstractField(ABC):
    """
    See https://docs.python.org/fr/3.10/howto/descriptor.html
    """

    __slots__ = ("default_value", "key")

    def __init__(self, default_value):
        self.default_value = default_value

    def _set_key(self, key):
        self.key = key

    def __get__(self, obj, objtype=None):
        if obj._local_copy:
            return obj._local_copy.get(self.key, self.default_value)
        return self.redis_get(obj, objtype)

    def __set__(self, obj, value):
        if obj._local_copy:
            obj._local_copy[self.key] = value
            return
        return self.redis_set(obj, value)

    def redis_get(self, obj, objtype=None):
        raw = get_redis_client().get(self.key)
        if raw is None:
            return self.default_value
        return self.deserialize(raw)

    def redis_set(self, obj, value):
        if value is None:
            get_redis_client().delete(self.key)
            return    
        raw = self.serialize(value)
        get_redis_client().set(self.key, raw)

    # implement __del__

    def __repr__(self):
        kv = []
        for k in dir(self):
            if k.startswith("_") or k == "key":
                continue
            v = getattr(self, k)
            if callable(v):
                continue
            kv.append(f"{k}={v!r}")
        kv_str = ", ".join(kv)
        return f"<{self.__class__.__name__} {kv_str}>"

    @abstractmethod
    def deserialize(self, raw: bytes):
        pass

    @abstractmethod
    def serialize(self, value) -> bytes:
        pass


class BytesField(AbstractField):
    def deserialize(self, raw):
        return raw

    def serialize(self, value):
        return value


class BooleanField(AbstractField):
    def deserialize(self, raw):
        return True if raw == b"\xFF" else False

    def serialize(self, value):
        return b"\xFF" if value else b"\x00"


class IntField(AbstractField):

    __slots__ = ("size", "signed")

    def __init__(self, default_value, size=4, signed=True):
        super().__init__(default_value)
        self.size = size
        self.signed = signed

    def deserialize(self, raw):
        return int.from_bytes(raw, "big", signed=self.signed)

    def serialize(self, value):
        return value.to_bytes(self.size, "big", signed=self.signed)


class StrField(AbstractField):
    deserialize = staticmethod(bytes.decode)
    serialize = staticmethod(str.encode)


class FloatField(AbstractField):
    def deserialize(self, raw):
        return struct.unpack("!d", raw)[0]

    def serialize(self, value):
        return struct.pack("!d", value)


class GenericField(AbstractField):
    def deserialize(self, raw):
        return pickle.loads(raw)

    def serialize(self, value):
        return pickle.dumps(value)


class LazyLoadField(AbstractField):
    """Initialize once the data using a provided function.
    Cache the value for a time, reload after timeout (call again the function).

    TODO
    """

    pass
