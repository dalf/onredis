from onredis import onredis, IntField
from redis_storage import get_redis_client
import cProfile
from typing import Optional, Dict

import redis.exceptions

@onredis  # <-- storage on Redis declared here
class DataStructClass:
    a: int = 5
    b: str = "bb"
    c: bool = False
    d: int = IntField(5, size=1, signed=False)  # <-- custom encoding. By defaut size=4 bytes, signed=True
    f: Dict[str, int]  # <-- f is going to be a hash store in Redis

    def test(self):
        # this is a normal class, so we can add a method
        # however the intent of @onredis is to declare a data class, 
        # not a general class
        return self.a + self.c


DataStruct = DataStructClass()
DataStruct.f = {
    'b': 5,
    'd': 4,
}
print(DataStruct.f)

DataStruct.f['a'] = 8
print(DataStruct.f)

print(DataStruct) # <-- @onredis has defined the __repr__ method

# import sys
# sys.exit(1)

def test():
    # the function is nearly 3 times faster with local_copy=True 
    # False: each access makes a Redis access
    # True: a local copy is done when the lock is acquired, then all the data are written when the lock is released
    with DataStruct.lock(local_copy=False):  # <-- the lock method is defined by @onredis
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

print('before', DataStruct)

test()

print('after1', DataStruct)

test()

print('after2', DataStruct)

test()

print('after3', DataStruct)



DataStruct.a = 4242  # <-- no need for a lock to modify the data, MyStruct.a += 1 is not going to work as expected without lock. 

profile_file_name = 'example.prof'

if profile_file_name:
    pr = cProfile.Profile()
    pr.enable()

import timeit
# 2 seconds on my laptop for 1000 iterations
print(timeit.timeit('test()', globals=globals(), number=3000))

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
