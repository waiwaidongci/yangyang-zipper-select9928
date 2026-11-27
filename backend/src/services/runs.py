import math

from fastapi import HTTPException
from sqlalchemy import select

from src.constants.workflow import Decision, Role, RunStatus
from src.domain.project import SPEC
from src.models.review import Review
from src.models.run import Run
from src.services.audit import record
from src.services.catalog import get_dataset
from src.services.queue import notify_worker
from src.utils.time import utc_stamp


def run_info(run, review):
    fields = ('id', 'label', 'dataset_id', 'created_at', 'status', 'settings')
    return {**{key: getattr(run, key) for key in fields}, 'decision': review.decision if review else None}


def list_runs(session, actor):
    statement = select(Run, Review).outerjoin(Review, Run.id == Review.run_id).order_by(Run.id.desc()).limit(100)
    if actor.role == Role.VIEWER:
        statement = statement.where(Review.decision == Decision.APPROVED)
    return [run_info(run, review) for run, review in session.execute(statement)]


def get_run(session, run_id, actor):
    run = session.get(Run, run_id)
    review = session.get(Review, run_id)
    if run is None or (actor.role == Role.VIEWER and (not review or review.decision != Decision.APPROVED)):
        raise LookupError('找不到可查看的运行')
    return run, review


def validate_settings(settings):
    parameters = {item['key']: item for item in SPEC['settings']}
    if settings.keys() - parameters.keys():
        raise ValueError('存在本项目未定义的运行参数')
    checked = {}
    for key, parameter in parameters.items():
        value = settings.get(key, parameter['default'])
        if not math.isfinite(value) or not parameter['min'] <= value <= parameter['max']:
            raise ValueError(f"{parameter['label']}超出范围")
        if parameter['step'] == 1 and value != int(value):
            raise ValueError(f"{parameter['label']}必须是整数")
        checked[key] = int(value) if parameter['step'] == 1 else value
    return checked


def create_run(session, payload, actor):
    get_dataset(session, payload.dataset_id)
    run = Run(label=payload.label, dataset_id=payload.dataset_id, created_by=actor.id,
              created_at=utc_stamp(), status=RunStatus.QUEUED, settings=validate_settings(payload.settings))
    session.add(run)
    session.flush()
    record(session, 'run.queued', run.id, actor.id)
    session.commit()
    notify_worker()
    return run_info(run, None)


def export_table(session, run_id, key, actor):
    run, review = get_run(session, run_id, actor)
    if review is None or review.decision != Decision.APPROVED:
        raise HTTPException(409, '复核通过后可下载正式 CSV')
    for table in run.result['tables']:
        if table['key'] == key:
            return table
    raise LookupError('找不到结果表')
