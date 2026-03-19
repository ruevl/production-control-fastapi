import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.db.session import sync_engine
from src.models.webhook import WebhookDelivery, WebhookSubscription


@celery_app.task(bind=True, max_retries=3)
def send_webhook_delivery(self, delivery_id: int):
    with Session(sync_engine) as db:
        delivery = db.execute(
            select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        ).scalar_one_or_none()

        if not delivery:
            return {"success": False, "error": "Delivery not found"}

        subscription = db.execute(
            select(WebhookSubscription).where(
                WebhookSubscription.id == delivery.subscription_id
            )
        ).scalar_one_or_none()

        if not subscription or not subscription.is_active:
            delivery.status = "failed"
            delivery.error_message = "Subscription not active"
            db.commit()
            return {"success": False, "error": "Subscription not active"}

        signature = hmac.new(
            subscription.secret_key.encode(),
            json.dumps(delivery.payload).encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Event": delivery.event_type,
        }

        try:
            with httpx.Client(timeout=subscription.timeout) as client:
                response = client.post(
                    subscription.url,
                    json=delivery.payload,
                    headers=headers
                )

                delivery.attempts += 1
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:1000]
                delivery.delivered_at = datetime.now(timezone.utc)

                if response.status_code < 400:
                    delivery.status = "success"
                    db.commit()
                    return {"success": True, "status_code": response.status_code}
                else:
                    delivery.status = "failed"
                    delivery.error_message = f"HTTP {response.status_code}"
                    db.commit()
                    raise ValueError(f"Bad HTTP status: {response.status_code}")

        except httpx.RequestError as exc:
            delivery.status = "failed"
            delivery.error_message = str(exc)
            delivery.attempts += 1
            db.commit()
            raise self.retry(exc=exc, countdown=60 * delivery.attempts)


async def trigger_webhook(db: AsyncSession, event_type: str, payload: dict):
    query = select(WebhookSubscription).where(
        WebhookSubscription.is_active == True,
        WebhookSubscription.events.contains([event_type])
    )
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    for subscription in subscriptions:
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type,
            payload=payload,
            status="pending",
            attempts=0
        )
        db.add(delivery)
        await db.flush()

        send_webhook_delivery.delay(delivery.id)