import abc
import typing
import redis
import redis.lock
from typing import _GenericAlias
from types import FunctionType
from redis_storage import get_redis_client

from .lock import OnRedisLock
from .fields import AbstractField, StrField, IntField, BooleanField, GenericField
from .dictionary_field import GenericDictionaryField, DictionaryField


FIELD_CLASSES = {
    str: StrField,
    int: IntField,
    bool: BooleanField,
    dict: DictionaryField,
    typing.Dict: DictionaryField,
    typing.Mapping: DictionaryField,
}


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
    expected_value = bytes(repr(cls.__fields__), encoding='utf-8')
    if value == expected_value:
        return
    # invalid field definition store on Redis
    # delete the data
    redis_client.set(key, expected_value)
    keys = [
        v.key
        for v in cls.__fields__.values()
    ]
    redis_client.delete(b' '.join(keys))


def _get_field(field_type, default_value):
    field_class_args = tuple()

    # create an instance of AbstractField or use the one provided as a default value
    if isinstance(default_value, AbstractField):
        # use the default
        return default_value

    # create a new instance of AbstractField
    if isinstance(field_type, _GenericAlias):
        field_class_args = [
            _get_field(t, None)
            for t in field_type.__args__
        ]
        field_type = field_type.__origin__
        print('bob', field_type)
    field_class = FIELD_CLASSES.get(field_type, GenericField)

    print(field_type, field_class, field_class_args)

    return field_class(*field_class_args, default_value=default_value)


def _process_class(cls):
    redis_prefix = f'{cls.__module__}.{cls.__name__}'
    redis_lock_name = redis_prefix + '!lock'
    redis_classid = redis_prefix + '!class'

    # initialize the fields
    _set_new_attribute(cls, '__fields__', {})
    cls__dict__ = cls.__dict__
    for field_name, field_type in cls__dict__.get('__annotations__', {}).items():
        redis_key = bytes(redis_prefix + '.' + field_name, encoding='utf-8')
        # read the default value and erase it
        default_value = None
        if field_name in cls__dict__:
            default_value = cls__dict__[field_name]
            delattr(cls, field_name)
        # create an instance of AbstractField or use the one provided as a default value
        field = _get_field(field_type, default_value)
        # set the Redis key
        field._set_key(redis_key)
        # update the class attribute
        _set_new_attribute(cls, field_name, field)
        cls.__fields__[field_name] = field

    # check if there are existing values in Redis with a previous definition of the class
    _delete_invalid_data_format(cls, redis_classid)

    # add methods
    def cls__repr__(self) -> str:
        values = [f'{field_name}={getattr(self, field_name)!r}' for field_name in self.__fields__.keys()]
        values_str = ', '.join(values)
        return f'<{cls.__name__} {values_str}>'
    
    def cls_lock(self, local_copy=False) -> OnRedisLock:
        lock = getattr(self, '_lock_value', None)
        if lock is None:
            redis_client = get_redis_client()
            lock = redis.lock.Lock(redis_client, redis_lock_name)
            self._lock_value = lock
        return OnRedisLock(self, cls, lock, local_copy)

    def cls__new__(ncls):
        # make there is only one instance since the Redis is on the class
        if not hasattr(cls, '_singleton'):
            cls._singleton = super(cls, ncls).__new__(cls)
        return cls._singleton

    _set_new_attribute(cls, '_local_copy', False)
    _set_new_attribute(cls, '__repr__', cls__repr__)
    _set_new_attribute(cls, 'lock', cls_lock)
    _set_new_attribute(cls, '__new__', cls__new__)

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
