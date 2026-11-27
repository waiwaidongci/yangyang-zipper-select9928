from redis import Redis, RedisError

from src.config.settings import REDIS_URL

redis_client = Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=3)
QUEUE_KEY = 'analysis-wakeup'


def notify_worker():
    try:
        with redis_client.pipeline() as pipe:
            pipe.lpush(QUEUE_KEY, 'ready').ltrim(QUEUE_KEY, 0, 0).execute()
    except RedisError:
        # The committed database queue is authoritative. The worker also polls it.
        pass
