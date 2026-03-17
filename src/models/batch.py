from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin
from src.models.mixins import PrimaryKeyMixin


class Batch(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "batches"

    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    task_description: Mapped[str] = mapped_column(String, nullable=False)
    work_center_id: Mapped[int] = mapped_column(Integer, ForeignKey("work_centers.id"), nullable=False)
    shift: Mapped[str] = mapped_column(String, nullable=False)
    team: Mapped[str] = mapped_column(String, nullable=False)

    batch_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    batch_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)

    nomenclature: Mapped[str] = mapped_column(String, nullable=False)
    ekn_code: Mapped[str] = mapped_column(String, nullable=False)

    shift_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    shift_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="batch",
        lazy="select",
        cascade="all, delete-orphan"
    )
    work_center: Mapped["WorkCenter"] = relationship(
        "WorkCenter",
        back_populates="batches",
        lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint("batch_number", "batch_date", name="uq_batch_number_date"),
        Index("idx_batch_closed", "is_closed"),
        Index("idx_batch_shift_times", "shift_start", "shift_end"),
        Index("idx_batch_work_center", "work_center_id"),
    )
