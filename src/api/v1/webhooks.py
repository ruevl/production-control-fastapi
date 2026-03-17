from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
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
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.patch("/subscriptions/{subscription_id}")
async def update_webhook_subscription(
        subscription_id: int,
        subscription_update: WebhookSubscriptionUpdate,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    update_data = subscription_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(subscription, field, value)

    await db.commit()
    await db.refresh(subscription)

    return WebhookSubscriptionResponse.model_validate(subscription)


@router.delete("/subscriptions/{subscription_id}")
async def delete_webhook_subscription(
        subscription_id: int,
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    await db.delete(subscription)
    await db.commit()

    return {"success": True, "message": "Subscription deleted"}


@router.post("/subscriptions/{subscription_id}/test")
async def test_webhook_subscription(
        subscription_id: int,
        db: AsyncSession = Depends(get_db)
):

    result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    test_payload = {
        "event": "test",
        "message": "This is a test webhook",
        "timestamp": "2024-01-01T00:00:00Z"
    }

    await trigger_webhook(db, "test", test_payload)
    await db.commit()

    return {
        "success": True,
        "message": "Test webhook sent",
        "payload": test_payload
    }


@router.get("/subscriptions/{subscription_id}/deliveries")
async def list_webhook_deliveries(
        subscription_id: int,
        status_filter: Optional[str] = Query(None, alias="status"),
        db: AsyncSession = Depends(get_db)
):
    sub_result = await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    query = select(WebhookDelivery).where(
        WebhookDelivery.subscription_id == subscription_id
    )

    if status_filter:
        query = query.where(WebhookDelivery.status == status_filter)

    query = query.order_by(WebhookDelivery.created_at.desc()).limit(50)

    result = await db.execute(query)
    deliveries = result.scalars().all()

    return WebhookDeliveryListResponse(
        items=[WebhookDeliveryResponse.model_validate(d) for d in deliveries],
        total=len(deliveries)
    )
