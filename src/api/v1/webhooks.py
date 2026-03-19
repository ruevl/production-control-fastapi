from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.models.webhook import WebhookDelivery, WebhookSubscription
from src.schemas.webhook import (
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)
from src.tasks.webhooks import trigger_webhook

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def get_subscription_or_404(subscription_id: int, db: AsyncSession) -> WebhookSubscription:
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return subscription


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
        subscription_data: WebhookSubscriptionCreate,
        db: AsyncSession = Depends(get_db)
):
    subscription = WebhookSubscription(
        url=subscription_data.url,
        events=subscription_data.events,
        secret_key=subscription_data.secret_key,
        is_active=subscription_data.is_active,
        retry_count=subscription_data.retry_count,
        timeout=subscription_data.timeout
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return WebhookSubscriptionResponse.model_validate(subscription)


@router.get("/subscriptions", response_model=list[WebhookSubscriptionResponse])
async def list_webhook_subscriptions(
        is_active: Optional[bool] = Query(None),
        db: AsyncSession = Depends(get_db)
):
    query = select(WebhookSubscription)
    if is_active is not None:
        query = query.where(WebhookSubscription.is_active == is_active)
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    return [WebhookSubscriptionResponse.model_validate(s) for s in subscriptions]


@router.get("/subscriptions/{subscription_id}")
async def get_webhook_subscription(
        subscription_id: int,
        db: AsyncSession = Depends(get_db)
):
    subscription = await get_subscription_or_404(subscription_id, db)
    return WebhookSubscriptionResponse.model_validate(subscription)


@router.patch("/subscriptions/{subscription_id}")
async def update_webhook_subscription(
        subscription_id: int,
        subscription_update: WebhookSubscriptionUpdate,
        db: AsyncSession = Depends(get_db)
):
    subscription = await get_subscription_or_404(subscription_id, db)

    update_data = subscription_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    await db.commit()
    await db.refresh(subscription)
    return WebhookSubscriptionResponse.model_validate(subscription)


@router.delete("/subscriptions/{subscription_id}")
async def delete_webhook_subscription(
        subscription_id: int,
        db: AsyncSession = Depends(get_db)
):
    subscription = await get_subscription_or_404(subscription_id, db)
    await db.delete(subscription)
    await db.commit()
    return {"success": True, "message": "Subscription deleted"}


@router.post("/subscriptions/{subscription_id}/test")
async def test_webhook_subscription(
        subscription_id: int,
        db: AsyncSession = Depends(get_db)
):
    await get_subscription_or_404(subscription_id, db)

    test_payload = {
        "event": "test",
        "message": "This is a test webhook",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    await trigger_webhook(db, "test", test_payload)
    await db.commit()
    return {"success": True, "message": "Test webhook sent", "payload": test_payload}


@router.get("/subscriptions/{subscription_id}/deliveries")
async def list_webhook_deliveries(
        subscription_id: int,
        status_filter: Optional[str] = Query(None, alias="status"),
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    await get_subscription_or_404(subscription_id, db)

    query = select(WebhookDelivery).where(
        WebhookDelivery.subscription_id == subscription_id
    )
    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)

    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar_one()

    query = query.order_by(WebhookDelivery.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    deliveries = result.scalars().all()

    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=total,
    )
