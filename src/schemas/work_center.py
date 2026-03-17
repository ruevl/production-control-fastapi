from datetime import datetime

from pydantic import BaseModel


class WorkCenterCreate(BaseModel):
    identifier: str
    name: str


class WorkCenterResponse(BaseModel):
    id: int
    identifier: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
