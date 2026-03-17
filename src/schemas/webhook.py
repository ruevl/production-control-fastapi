from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WebhookSubscriptionCreate(BaseModel):
    url: str
    events: list[str]
    secret_key: str
    is_active: bool = True
    retry_count: int = 3
    timeout: int = 10


class WebhookSubscriptionUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[list[str]] = None
    secret_key: Optional[str] = None
    is_active: Optional[bool] = None
    retry_count: Optional[int] = None
    timeout: Optional[int] = None


class WebhookSubscriptionResponse(BaseModel):
    id: int
    url: str
    events: list[str]
    is_active: bool
    retry_count: int
    timeout: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: int
    subscription_id: int
    event_type: str
    status: str
    attempts: int
    response_status: Optional[int] = None
    created_at: datetime
    delivered_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
    total: int
