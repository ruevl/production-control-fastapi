from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin
from src.models.mixins import PrimaryKeyMixin


class WorkCenter(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "work_centers"

    identifier: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    batches: Mapped[list["Batch"]] = relationship(
        "Batch",
        back_populates="work_center",
        lazy="select"
    )
