"""Webhook dispatcher for async event notifications."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from visionscore.api.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# Retry schedule: attempt 2 after 30s, attempt 3 after 2min, attempt 4 after 10min
_RETRY_DELAYS = [30, 120, 600]


class WebhookDispatcher:
    """Dispatches webhook events to registered URLs."""

    def __init__(self, db: SupabaseClient) -> None:
        self._db = db

    async def dispatch(self, event: str, payload: dict) -> None:
        """Send *event* with *payload* to all active webhooks subscribed to it."""
        webhooks = await self._db.get_active_webhooks_for_event(event)
        for wh in webhooks:
            try:
                await self.deliver_one(wh, event, payload)
            except Exception as e:
                logger.warning("Webhook delivery failed for %s: %s", wh.get("id"), e)

    async def deliver_one(
        self, webhook: dict, event: str, payload: dict, attempt: int = 1
    ) -> bool:
        """Deliver a single webhook. Returns True on success."""
        body = json.dumps({"event": event, "payload": payload, "timestamp": datetime.now(timezone.utc).isoformat()})
        headers: dict[str, str] = {"Content-Type": "application/json"}

        secret = webhook.get("secret")
        if secret:
            sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-VisionScore-Signature"] = sig

        status_code = None
        response_body = None
        success = False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook["url"], content=body, headers=headers)
                status_code = resp.status_code
                response_body = resp.text[:2000]
                success = 200 <= resp.status_code < 300
        except Exception as e:
            response_body = str(e)

        # Schedule retry if failed
        next_retry = None
        if not success and attempt <= len(_RETRY_DELAYS):
            delay = _RETRY_DELAYS[attempt - 1]
            next_retry = (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat()

        await self._db.record_webhook_delivery(
            webhook_id=webhook["id"],
            event=event,
            payload=payload,
            status_code=status_code,
            response_body=response_body,
            success=success,
            attempt=attempt,
            next_retry_at=next_retry,
        )

        return success

    async def retry_failed(self) -> int:
        """Retry failed deliveries that are past their next_retry_at. Returns count retried."""
        deliveries = await self._db.get_failed_deliveries_for_retry()
        retried = 0
        for delivery in deliveries:
            webhook_id = delivery["webhook_id"]
            webhooks = await self._db.list_webhooks()
            wh = next((w for w in webhooks if w["id"] == webhook_id and w.get("is_active", True)), None)
            if wh is None:
                continue

            await self.deliver_one(wh, delivery["event"], delivery["payload"], attempt=delivery["attempt"] + 1)
            retried += 1

        return retried
