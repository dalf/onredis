#!/bin/bash

docker stop redis
docker run --rm --name redis -v $(pwd)/redis:/tmp -v $(pwd)/redis.conf:/etc/redis.conf redis redis-server /etc/redis.conf
