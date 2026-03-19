from typing import Any, Optional

from pydantic import BaseModel


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None


class TaskProgress(BaseModel):
    current: int
    total: int
    progress: int
