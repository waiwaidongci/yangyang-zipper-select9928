from fastapi import APIRouter

from src.controllers.dependencies import Actor, Db
from src.schemas.auth import Credentials, Identity, Token
from src.services.accounts import sign_in

router = APIRouter(prefix='/auth')


@router.post('/login', response_model=Token)
def login(payload: Credentials, session: Db):
    return sign_in(session, payload)


@router.get('/me', response_model=Identity)
def identity(actor: Actor):
    return {'email': actor.email, 'role': actor.role}
