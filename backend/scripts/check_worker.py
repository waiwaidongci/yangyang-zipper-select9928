import time

from src.config.settings import ARTIFACT_DIR

heartbeat = ARTIFACT_DIR / 'worker.heartbeat'
raise SystemExit(0 if heartbeat.exists() and time.time() - heartbeat.stat().st_mtime < 90 else 1)
