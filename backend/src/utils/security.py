import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from src.config.settings import JWT_SECRET


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200_000)
    return f'{salt}${derived.hex()}'


def matches(password, encoded):
    return hmac.compare_digest(hash_password(password, encoded.split('$')[0]), encoded)


def token_for(account_id):
    now = datetime.now(timezone.utc)
    return jwt.encode({'sub': str(account_id), 'iat': now, 'exp': now + timedelta(hours=8)}, JWT_SECRET, algorithm='HS256')


def token_subject(token):
    return int(jwt.decode(token, JWT_SECRET, algorithms=['HS256'], options={'require': ['exp', 'sub']})['sub'])
