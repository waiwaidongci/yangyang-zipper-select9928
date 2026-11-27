from fastapi import HTTPException
from sqlalchemy import select

from src.constants.workflow import RunStatus
from src.models.review import Review
from src.models.run import Run
from src.services.audit import record
from src.utils.time import utc_stamp


def review_info(review):
    return {'run_id': review.run_id, 'decision': review.decision, 'note': review.note, 'created_at': review.created_at}


def submit(session, run_id, payload, actor):
    run = session.scalar(select(Run).where(Run.id == run_id).with_for_update())
    if not run:
        raise LookupError('找不到运行')
    if run.status != RunStatus.COMPLETED or session.get(Review, run_id):
        raise HTTPException(409, '仅可复核一次，且计算必须成功完成')
    review = Review(run_id=run_id, reviewer_id=actor.id, decision=payload.decision,
                    note=payload.note, created_at=utc_stamp())
    session.add(review)
    record(session, 'review.' + payload.decision, run_id, actor.id)
    session.commit()
    return review_info(review)
