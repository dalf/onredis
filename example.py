from onredis import onredis, set_redis_client, get_redis_client
from onredis.fields import IntField
import threading
import cProfile
from typing import Optional, Dict

import redis.exceptions


@onredis  # <-- storage on Redis declared here
class DataStructClass:
    a: int = 5
    b: str = "bb"
    c: Optional[bool] = False
    d: int = IntField(5, size=1, signed=False)  # <-- custom encoding. By defaut size=4 bytes, signed=True
    f: Dict[str, int] = {} # <-- the f key is going to be a hash store in Redis
    g: Optional[float]

    def test(self):
        # this is a normal class, so we can add a method
        # however the intent of @onredis is to declare a data class, 
        # not a general class
        return self.a + self.c


set_redis_client(redis.Redis(unix_socket_path='./redis/docker/redis.sock'))


# this is a singleton, another instance is going to be the same object
DataStruct = DataStructClass()  # <-- this is where the Redis client is required

print(DataStruct.test())

DataStruct.g = 3.1415927
print(DataStruct.g)

DataStruct.g = None

print(DataStruct) # <-- @onredis has defined the __repr__ method

DataStruct.g = 13.37

def test():
    with DataStruct.transaction():
        # do some random stuff
        DataStruct.a += 1
        if DataStruct.a % 2 == 0:
            DataStruct.b += chr(65 + (DataStruct.a % 26)) + chr(96 + (DataStruct.a % 26))
        else:
            DataStruct.b = DataStruct.b[2:]
        DataStruct.c = not DataStruct.c
        DataStruct.f['a'] = len(DataStruct.b)
        DataStruct.f[DataStruct.b] = DataStruct.f['a'] * 2
        DataStruct.d = (DataStruct.d | DataStruct.a) & 255


def loop():
    ok = 0
    conflict = 0
    for i in range(1, 10):
        try:
            test()
            ok += 1
        except redis.exceptions.WatchError:
            conflict += 1
    print('ok', ok, 'conflict', conflict)


def multithread():
    t_list = []
    for _ in range(1, 10):
        t = threading.Thread(target=loop)
        t.setDaemon(True)
        t.start()
        t_list.append(t)
    for t in t_list:
        t.join()


# multithread()

print('before', DataStruct)

test()

print('after1', DataStruct)

test()

print('after2', DataStruct)

test()

print('after3', DataStruct)



DataStruct.a = 4242  # <-- no need for a lock to modify the data, MyStruct.a += 1 is not going to work as expected without lock. 

profile_file_name = False # 'example.prof'

if profile_file_name:
    pr = cProfile.Profile()
    pr.enable()

import timeit
# 2 seconds on my laptop for 1000 iterations
print(timeit.timeit('test()', globals=globals(), number=10000))

if profile_file_name:
    pr.disable()
    pr.dump_stats(profile_file_name)

print(DataStruct)

####################

print('\nRedis keys\n')
redis_client = get_redis_client()
for k in redis_client.keys():
    try:
        v = redis_client.get(k) 
    except redis.exceptions.ResponseError:
        v = redis_client.hgetall(k)
    print(k, '=', v)
