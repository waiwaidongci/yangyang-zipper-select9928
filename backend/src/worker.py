import logging
import time

from redis import RedisError

from src.config.settings import ARTIFACT_DIR
from src.services.execution import claim, execute, recover_jobs
from src.services.queue import QUEUE_KEY, redis_client


def heartbeat():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / 'worker.heartbeat').touch()


def worker():
    logging.basicConfig(level=logging.INFO)
    recover_jobs()
    while True:
        heartbeat()
        job = claim()
        if job is not None:
            execute(job)
            continue
        try:
            redis_client.brpop(QUEUE_KEY, timeout=2)
        except RedisError:
            time.sleep(1)


if __name__ == '__main__':
    worker()
