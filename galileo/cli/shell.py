import os

import redis

import pymq
from galileo.controller import ExperimentController, ExperimentShell
from pymq.provider.redis import RedisConfig


def main():
    rds = redis.Redis(
        host=os.getenv('galileo_redis_host', 'localhost'),
        port=int(os.getenv('galileo_redis_port', 6379)),
        decode_responses=True
    )
    pymq.init(RedisConfig(rds))

    ctrl = ExperimentController(rds)
    ExperimentShell(ctrl).run()


if __name__ == '__main__':
    main()
