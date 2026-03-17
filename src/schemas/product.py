from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProductCreate(BaseModel):
    unique_code: str
    batch_id: int


class ProductAggregate(BaseModel):
    unique_code: str


class ProductResponse(BaseModel):
    id: int
    unique_code: str
    batch_id: int
    is_aggregated: bool
    aggregated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
