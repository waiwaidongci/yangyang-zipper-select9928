from src.models.audit import Audit
from src.utils.time import utc_stamp


def record(session, action, object_id, actor_id=None):
    session.add(Audit(action=action, object_id=object_id, actor_id=actor_id, created_at=utc_stamp()))
