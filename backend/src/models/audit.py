from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class Audit(Base):
    __tablename__ = 'audit_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('accounts.id'))
    action: Mapped[str] = mapped_column(String(48))
    object_id: Mapped[int] = mapped_column()
    created_at: Mapped[str] = mapped_column(String(32))
