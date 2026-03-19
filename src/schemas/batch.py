from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class OneCFields:
    TASK_DESCRIPTION = "ПредставлениеЗаданияНаСмену"
    WORK_CENTER_ID = "ИдентификаторРЦ"
    SHIFT = "Смена"
    TEAM = "Бригада"
    BATCH_NUMBER = "НомерПартии"
    BATCH_DATE = "ДатаПартии"
    NOMENCLATURE = "Номенклатура"
    EKN_CODE = "КодЕКН"
    SHIFT_START = "ДатаВремяНачалаСмены"
    SHIFT_END = "ДатаВремяОкончанияСмены"


class BatchCreate(BaseModel):
    is_closed: bool = False
    task_description: str = Field(..., alias=OneCFields.TASK_DESCRIPTION)
    work_center_identifier: str = Field(..., alias=OneCFields.WORK_CENTER_ID)
    shift: str = Field(..., alias=OneCFields.SHIFT)
    team: str = Field(..., alias=OneCFields.TEAM)
    batch_number: int = Field(..., alias=OneCFields.BATCH_NUMBER)
    batch_date: date = Field(..., alias=OneCFields.BATCH_DATE)
    nomenclature: str = Field(..., alias=OneCFields.NOMENCLATURE)
    ekn_code: str = Field(..., alias=OneCFields.EKN_CODE)
    shift_start: datetime = Field(..., alias=OneCFields.SHIFT_START)
    shift_end: datetime = Field(..., alias=OneCFields.SHIFT_END)

    class Config:
        populate_by_name = True


class BatchUpdate(BaseModel):
    is_closed: Optional[bool] = None
    task_description: Optional[str] = None
    shift: Optional[str] = None
    team: Optional[str] = None
    nomenclature: Optional[str] = None
    ekn_code: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None


class BatchResponse(BaseModel):
    id: int
    is_closed: bool
    closed_at: Optional[datetime] = None
    task_description: str
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime
    work_center_id: int

    class Config:
        from_attributes = True


class BatchDetailResponse(BatchResponse):
    products: list["ProductResponse"]


class BatchListResponse(BaseModel):
    items: list[BatchResponse]
    total: int
    offset: int
    limit: int


from src.schemas.product import ProductResponse

BatchDetailResponse.model_rebuild()
