import asyncio
import hashlib
import hmac
import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.celery_app import celery_app
from src.db.session import engine
from src.models.webhook import WebhookDelivery, WebhookSubscription


@celery_app.task(bind=True, max_retries=3)
def send_webhook_delivery(self, delivery_id: int):
    """
    Отправка webhook с retry логикой.
    """
    try:
        async def _send():
            async with AsyncSession(engine) as db:
                # Get delivery
                delivery_query = select(WebhookDelivery).where(
                    WebhookDelivery.id == delivery_id
                )
                delivery_result = await db.execute(delivery_query)
                delivery = delivery_result.scalar_one_or_none()

                if not delivery:
                    return {"success": False, "error": "Delivery not found"}

                # Get subscription
                subscription_query = select(WebhookSubscription).where(
                    WebhookSubscription.id == delivery.subscription_id
                )
                subscription_result = await db.execute(subscription_query)
                subscription = subscription_result.scalar_one_or_none()

                if not subscription or not subscription.is_active:
                    delivery.status = "failed"
                    delivery.error_message = "Subscription not active"
                    await db.commit()
                    return {"success": False, "error": "Subscription not active"}

                # Calculate HMAC signature
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
                    async with httpx.AsyncClient(
                            timeout=subscription.timeout
                    ) as client:
                        response = await client.post(
                            subscription.url,
                            json=delivery.payload,
                            headers=headers
                        )

                        delivery.status = "success" if response.status_code < 400 else "failed"
                        delivery.response_status = response.status_code
                        delivery.response_body = response.text[:1000]  # Limit size
                        delivery.attempts += 1
                        delivery.delivered_at = datetime.utcnow()

                        if delivery.status == "success":
                            await db.commit()
                            return {
                                "success": True,
                                "status_code": response.status_code
                            }
                        else:
                            delivery.error_message = f"HTTP {response.status_code}"
                            await db.commit()
                            self.retry(countdown=60 * delivery.attempts)

                except httpx.RequestError as exc:
                    delivery.status = "failed"
                    delivery.error_message = str(exc)
                    delivery.attempts += 1
                    await db.commit()
                    self.retry(countdown=60 * delivery.attempts)

        return asyncio.run(_send())

    except Exception as exc:
        self.retry(exc=exc, countdown=300)


async def trigger_webhook(db: AsyncSession, event_type: str, payload: dict):
    """
    Триггер для отправки webhook.
    """
    # Find active subscriptions for this event
    query = select(WebhookSubscription).where(
        WebhookSubscription.is_active == True,
        WebhookSubscription.events.contains([event_type])
    )
    result = await db.execute(query)
    subscriptions = result.scalars().all()

    for subscription in subscriptions:
        # Create delivery record
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_type=event_type,
            payload=payload,
            status="pending",
            attempts=0
        )
        db.add(delivery)
        await db.flush()

        # Send async
        send_webhook_delivery.delay(delivery.id)
