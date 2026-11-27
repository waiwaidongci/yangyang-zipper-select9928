from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from src.config.database import session_scope
from src.constants.workflow import Role
from src.models.account import Account
from src.utils.security import token_subject

Db = Annotated[Session, Depends(session_scope)]
Bearer = Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]


def authenticated(session: Db, authorization: Bearer):
    if authorization is not None:
        try:
            actor = session.get(Account, token_subject(authorization.credentials))
            if actor is not None:
                return actor
        except (InvalidTokenError, ValueError):
            pass
    raise HTTPException(401, '请先登录')


Actor = Annotated[Account, Depends(authenticated)]


def require_writer(actor: Actor):
    if actor.role == Role.VIEWER:
        raise HTTPException(403, '当前角色没有录入或运行权限')
    return actor


def require_admin(actor: Actor):
    if actor.role != Role.ADMIN:
        raise HTTPException(403, '复核与审计需要负责人权限')
    return actor


Writer = Annotated[Account, Depends(require_writer)]
Admin = Annotated[Account, Depends(require_admin)]
