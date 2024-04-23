import redis

from common.config import env_settings


def get_redis_conn():
    pool = redis.ConnectionPool(
        host=env_settings.REDIS_HOST,
        port=env_settings.REDIS_PORT,
        db=0,
        max_connections=50,
        socket_timeout=10,
        password=env_settings.REDIS_PWD,
        decode_responses=True,
    )
    return redis.Redis(connection_pool=pool)
