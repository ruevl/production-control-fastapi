from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin
from src.models.mixins import PrimaryKeyMixin


class Product(Base, PrimaryKeyMixin, TimestampMixin):
    __tablename__ = "products"

    unique_code: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(Integer, ForeignKey("batches.id"), nullable=False, index=True)

    is_aggregated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    aggregated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped["Batch"] = relationship(
        "Batch",
        back_populates="products",
        lazy="joined"
    )

    __table_args__ = (
        Index("idx_product_batch_aggregated", "batch_id", "is_aggregated"),
    )
