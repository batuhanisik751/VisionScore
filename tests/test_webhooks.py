"""Tests for webhook system."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from visionscore.api.app import app
from visionscore.api.supabase_client import reset_supabase_client
from visionscore.api.webhooks import WebhookDispatcher


@pytest.fixture(autouse=True)
def _reset_sb():
    reset_supabase_client()
    yield
    reset_supabase_client()


# ---------------------------------------------------------------------------
# Webhook CRUD endpoint tests
# ---------------------------------------------------------------------------


class TestWebhookEndpoints:
    def test_create_webhook(self):
        mock_db = AsyncMock()
        mock_db.create_webhook = AsyncMock(return_value="wh-1")

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.post(
                "/api/v1/webhooks",
                json={"url": "https://example.com/hook", "events": ["analysis.completed"]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "wh-1"
            assert data["url"] == "https://example.com/hook"
            assert data["is_active"] is True

    def test_create_webhook_invalid_event(self):
        mock_db = AsyncMock()

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.post(
                "/api/v1/webhooks",
                json={"url": "https://example.com", "events": ["invalid.event"]},
            )
            assert resp.status_code == 400

    def test_list_webhooks(self):
        mock_db = AsyncMock()
        mock_db.list_webhooks = AsyncMock(return_value=[
            {
                "id": "wh-1", "url": "https://example.com/hook",
                "events": ["analysis.completed"], "is_active": True,
                "created_at": "2025-01-01T00:00:00",
                "last_triggered_at": None, "failure_count": 0,
            }
        ])

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/webhooks")
            assert resp.status_code == 200
            assert len(resp.json()["webhooks"]) == 1

    def test_delete_webhook(self):
        mock_db = AsyncMock()
        mock_db.delete_webhook = AsyncMock(return_value=True)

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.delete("/api/v1/webhooks/wh-1")
            assert resp.status_code == 200

    def test_delete_webhook_not_found(self):
        mock_db = AsyncMock()
        mock_db.delete_webhook = AsyncMock(return_value=False)

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.delete("/api/v1/webhooks/nonexistent")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# WebhookDispatcher unit tests
# ---------------------------------------------------------------------------


class TestWebhookDispatcher:
    async def test_dispatches_to_matching_webhooks(self):
        mock_db = AsyncMock()
        mock_db.get_active_webhooks_for_event = AsyncMock(return_value=[
            {"id": "wh-1", "url": "https://example.com/hook", "secret": None},
        ])
        mock_db.record_webhook_delivery = AsyncMock()
        mock_db.list_webhooks = AsyncMock(return_value=[])

        dispatcher = WebhookDispatcher(mock_db)

        with patch("visionscore.api.webhooks.httpx") as mock_httpx:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            await dispatcher.dispatch("analysis.completed", {"report_id": "r1"})

            mock_client.post.assert_called_once()
            mock_db.record_webhook_delivery.assert_called_once()
            call_kwargs = mock_db.record_webhook_delivery.call_args[1]
            assert call_kwargs["success"] is True
            assert call_kwargs["event"] == "analysis.completed"

    async def test_skips_when_no_webhooks(self):
        mock_db = AsyncMock()
        mock_db.get_active_webhooks_for_event = AsyncMock(return_value=[])

        dispatcher = WebhookDispatcher(mock_db)
        await dispatcher.dispatch("analysis.completed", {"report_id": "r1"})

        mock_db.record_webhook_delivery.assert_not_called()

    async def test_records_failure_on_http_error(self):
        mock_db = AsyncMock()
        mock_db.get_active_webhooks_for_event = AsyncMock(return_value=[
            {"id": "wh-1", "url": "https://example.com/hook", "secret": None},
        ])
        mock_db.record_webhook_delivery = AsyncMock()

        dispatcher = WebhookDispatcher(mock_db)

        with patch("visionscore.api.webhooks.httpx") as mock_httpx:
            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            await dispatcher.dispatch("analysis.completed", {"report_id": "r1"})

            call_kwargs = mock_db.record_webhook_delivery.call_args[1]
            assert call_kwargs["success"] is False
            assert call_kwargs["next_retry_at"] is not None

    async def test_hmac_signature_when_secret_set(self):
        mock_db = AsyncMock()
        mock_db.record_webhook_delivery = AsyncMock()

        dispatcher = WebhookDispatcher(mock_db)

        with patch("visionscore.api.webhooks.httpx") as mock_httpx:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            webhook = {"id": "wh-1", "url": "https://example.com", "secret": "mysecret"}
            await dispatcher.deliver_one(webhook, "test.ping", {"msg": "hi"})

            call_args = mock_client.post.call_args
            headers = call_args[1]["headers"]
            assert "X-VisionScore-Signature" in headers

            # Verify the signature is correct
            body = call_args[1]["content"]
            expected_sig = hmac.new(b"mysecret", body.encode(), hashlib.sha256).hexdigest()
            assert headers["X-VisionScore-Signature"] == expected_sig

    async def test_retry_failed_deliveries(self):
        mock_db = AsyncMock()
        mock_db.get_failed_deliveries_for_retry = AsyncMock(return_value=[
            {"webhook_id": "wh-1", "event": "analysis.completed", "payload": {}, "attempt": 1},
        ])
        mock_db.list_webhooks = AsyncMock(return_value=[
            {"id": "wh-1", "url": "https://example.com", "secret": None, "is_active": True},
        ])
        mock_db.record_webhook_delivery = AsyncMock()

        dispatcher = WebhookDispatcher(mock_db)

        with patch("visionscore.api.webhooks.httpx") as mock_httpx:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.text = "OK"
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client

            count = await dispatcher.retry_failed()

            assert count == 1
            call_kwargs = mock_db.record_webhook_delivery.call_args[1]
            assert call_kwargs["attempt"] == 2
