import os
from pathlib import Path

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///local.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
JWT_SECRET = os.getenv('JWT_SECRET', 'only-for-local-development-please-change')
SEED_DEMO = os.getenv('SEED_DEMO', 'true').lower() == 'true'
ARTIFACT_DIR = Path(os.getenv('ARTIFACT_DIR', '/artifacts'))
