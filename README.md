# OnRedis

Store object on Redis.

```python
from typing import Dict
from onredis import onredis, set_redis_client, get_redis_client
import redis


@onredis
class Scores:
    total: float = 0
    count: int = 0
    total_per_type: Dict[str, float] = {} # <-- the f key is going to be a hash store in Redis
    count_per_type: Dict[str, float] = {} # <-- the f key is going to be a hash store in Redis

    def global_avg(self):
        return self.total / self.count

    def avg(self, key):
        return self.total_per_type[key] / self.count_per_type[key]

    def add(self, key, value):
        with self.transaction() as t:  
            # from now, all the fields are local values
            self.total += value
            self.count += 1
            self.total_per_type[key] = self.total_per_type.get(key, 0) + value
            self.count_per_type[key] = self.count_per_type.get(key, 0) + 1
            # when the transaction exits, all the value are written to Redis 
            # except if t.discard() has been called
            #
            # the end of the transaction can raise redis.exceptions.WatchError
            # if another thread or process has changed the same object

set_redis_client(redis.Redis(unix_socket_path='./redis/docker/redis.sock'))

scores = Scores()  # <-- this is a singleton Scores() elsewhere is going to return the same object

scores.add('debian', 3.5)
scores.add('fedora', 3.4)
scores.add('debian', 4.5)
scores.add('ubuntu', 3)
scores.add('ubuntu', 4.1)
print('global_avg=', scores.global_avg())
print('avg("ubuntu")=', scores.avg("ubuntu"))
print('data=', scores)

####################

print('\nRedis keys\n')
redis_client = get_redis_client()
for k in redis_client.keys():
    try:
        v = redis_client.get(k) 
    except redis.exceptions.ResponseError:
        v = redis_client.hgetall(k)
    print(k, '=', v)
```

Output:

```
global_avg= 3.7
avg("ubuntu")= 3.55
data= <Scores total=18.5, count=5, total_per_type={'debian': 8.0, 'fedora': 3.4, 'ubuntu': 7.1}, count_per_type={'debian': 2.0, 'fedora': 1.0, 'ubuntu': 2.0}>

Redis keys

b'__main__.Scores.total' = b'@2\x80\x00\x00\x00\x00\x00'
b'__main__.Scores.total_per_type' = {b'debian': b'@ \x00\x00\x00\x00\x00\x00', b'fedora': b'@\x0b333333', b'ubuntu': b'@\x1cffffff'}
b'__main__.Scores.count' = b'\x00\x00\x00\x05'
b'__main__.Scores.count_per_type' = {b'debian': b'@\x00\x00\x00\x00\x00\x00\x00', b'fedora': b'?\xf0\x00\x00\x00\x00\x00\x00', b'ubuntu': b'@\x00\x00\x00\x00\x00\x00\x00'}
b'__main__.Scores!class' = b"{'total': <FloatField default_value=0>, 'count': <IntField default_value=0, signed=True, size=4>, 'total_per_type': <DictionaryField default_value={}, key_field=<StrField default_value=None>, value_field=<FloatField default_value=None>>, 'count_per_type': <DictionaryField default_value={}, key_field=<StrField default_value=None>, value_field=<FloatField default_value=None>>}"
```
