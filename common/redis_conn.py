from functools import lru_cache

import redis
from loguru import logger

from common.config import env_settings

REDIS_HOST = env_settings.REDIS_HOST
REDIS_PORT = env_settings.REDIS_PORT


@lru_cache(1)
def get_redis():

    logger.info(f"creating redis connection with {REDIS_HOST=} {REDIS_PORT=}")
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=True,
    )
    return redis.Redis(connection_pool=redis_pool)
