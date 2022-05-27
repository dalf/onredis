import redis
import redis.lock
from types import FunctionType

from .client import get_redis_client, set_redis_client
from .lock import OnRedisLock
from .fields import get_field


__all__ = ("onredis", "set_redis_client", "get_redis_client", "OnRedisLock")


def _set_qualname(cls, value):
    # Ensure that the functions returned from _create_fn uses the proper
    # __qualname__ (the class they belong to).
    if isinstance(value, FunctionType):
        value.__qualname__ = f"{cls.__qualname__}.{value.__name__}"
    return value


def _set_new_attribute(cls, name, value):
    # Never overwrites an existing attribute.  Returns True if the
    # attribute already exists.
    if name in cls.__dict__:
        return True
    _set_qualname(cls, value)
    setattr(cls, name, value)
    return False


def _delete_invalid_data_format(cls, key):
    redis_client = get_redis_client()
    value = redis_client.get(key)
    expected_value = bytes(repr(cls.__fields__), encoding="utf-8")
    if value == expected_value:
        return
    # invalid field definition store on Redis
    # delete the data
    redis_client.set(key, expected_value)
    keys = [v.key for v in cls.__fields__.values()]
    redis_client.delete(b" ".join(keys))


def _process_class(cls):
    redis_prefix = f"{cls.__module__}.{cls.__name__}"
    redis_lock_name = redis_prefix + "!lock"
    redis_classid = redis_prefix + "!class"

    # initialize the fields
    _set_new_attribute(cls, "__fields__", {})
    cls__dict__ = cls.__dict__
    for field_name, field_type in cls__dict__.get("__annotations__", {}).items():
        redis_key = bytes(redis_prefix + "." + field_name, encoding="utf-8")
        # read the default value and erase it
        default_value = None
        if field_name in cls__dict__:
            default_value = cls__dict__[field_name]
            delattr(cls, field_name)
        # create an instance of AbstractField or use the one provided as a default value
        field = get_field(field_type, default_value)
        # set the Redis key
        field._set_key(redis_key)
        # update the class attribute
        _set_new_attribute(cls, field_name, field)
        cls.__fields__[field_name] = field

    # add methods
    def cls__repr__(self) -> str:
        values = [
            f"{field_name}={getattr(self, field_name)!r}"
            for field_name in self.__fields__.keys()
        ]
        values_str = ", ".join(values)
        return f"<{cls.__name__} {values_str}>"

    def cls_lock(self, local_copy=False) -> OnRedisLock:
        lock = getattr(self, "_lock_value", None)
        if lock is None:
            redis_client = get_redis_client()
            lock = redis.lock.Lock(redis_client, redis_lock_name)
            self._lock_value = lock
        return OnRedisLock(self, cls, lock, local_copy)

    def cls__new__(ncls):
        # check if there are existing values in Redis with a previous definition of the class
        _delete_invalid_data_format(cls, redis_classid)
        # make there is only one instance since the Redis is on the class
        if not hasattr(cls, "_singleton"):
            cls._singleton = super(cls, ncls).__new__(cls)
        return cls._singleton

    _set_new_attribute(cls, "_local_copy", False)
    _set_new_attribute(cls, "__repr__", cls__repr__)
    _set_new_attribute(cls, "lock", cls_lock)
    _set_new_attribute(cls, "__new__", cls__new__)

    # define __slots__
    # cls_dict = dict(cls.__dict__)
    # cls_dict['__slots__'] = tuple('_lock', '_lock_value')
    # for field_name in cls.__fields__:
    #     cls_dict.pop(field_name, None)
    # cls_dict.pop('__dict__', None)

    # Python 3.10
    # abc.update_abstractmethods(cls)

    return cls


def onredis(cls):
    def wrap(cls):
        return _process_class(cls)

    return wrap(cls)
