from fastapi import HTTPException
from sqlalchemy import select

from src.models.account import Account
from src.utils.security import hash_password, matches, token_for


def sign_in(session, credentials):
    email = credentials.email.strip().lower()
    actor = session.scalar(select(Account).where(Account.email == email))
    encoded = actor.password_hash if actor else '00' * 16 + '$' + '00' * 32
    if not matches(credentials.password, encoded) or actor is None:
        raise HTTPException(401, '邮箱或口令不正确')
    return {'access_token': token_for(actor.id), 'email': actor.email, 'role': actor.role}
