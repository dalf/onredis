# OnRedis

Store object on Redis.

```python
from typing import Dict
from onredis import onredis, set_redis_client
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
            self.total += value
            self.count += 1
            self.total_per_type[key] = self.total_per_type.get(key, 0) + value
            self.count_per_type[key] = self.count_per_type.get(key, 0) + 1
            # t.discard() to discard the transaction (all are going to be reverted)

set_redis_client(redis.Redis())

scores = Scores()

scores.add('debian', 3.5)
scores.add('fedora', 3.4)
scores.add('debian', 4.5)
scores.add('ubuntu', 3)
scores.add('ubuntu', 4.1)
print('global_avg=', scores.global_avg())
print('avg("fedora")=', scores.avg("fedora"))
print('data=', scores)
```
