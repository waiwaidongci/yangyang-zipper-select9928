from fastapi import APIRouter
from sqlalchemy import select, text

from src.controllers.dependencies import Admin, Db
from src.domain.project import SPEC
from src.models.audit import Audit
from src.services.queue import redis_client

router = APIRouter()


@router.get('/health')
def health(session: Db):
    session.execute(text('SELECT 1'))
    redis_client.ping()
    return {'status': 'ok'}


@router.get('/spec')
def project_spec():
    return SPEC


@router.get('/audit')
def events(session: Db, actor: Admin):
    fields = ('id', 'actor_id', 'action', 'object_id', 'created_at')
    return [{key: getattr(event, key) for key in fields} for event in session.scalars(
        select(Audit).order_by(Audit.id.desc()).limit(50))]
