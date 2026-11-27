from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    run_id: Mapped[int] = mapped_column(ForeignKey('analysis_runs.id'), primary_key=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'))
    decision: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))
