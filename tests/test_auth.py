"""Tests for API key authentication module and endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from visionscore.api.app import app
from visionscore.api.auth import generate_api_key, hash_api_key
from visionscore.api.supabase_client import reset_supabase_client


@pytest.fixture(autouse=True)
def _reset_sb():
    reset_supabase_client()
    yield
    reset_supabase_client()


# ---------------------------------------------------------------------------
# Unit tests for key generation / hashing
# ---------------------------------------------------------------------------


class TestHashApiKey:
    def test_produces_consistent_hash(self):
        h1 = hash_api_key("vs_abc123")
        h2 = hash_api_key("vs_abc123")
        assert h1 == h2

    def test_different_keys_different_hashes(self):
        h1 = hash_api_key("vs_abc123")
        h2 = hash_api_key("vs_xyz789")
        assert h1 != h2


class TestGenerateApiKey:
    def test_key_format(self):
        raw, key_hash = generate_api_key()
        assert raw.startswith("vs_")
        assert len(raw) == 35  # "vs_" + 32 hex chars

    def test_hash_matches_generated_key(self):
        raw, key_hash = generate_api_key()
        assert hash_api_key(raw) == key_hash

    def test_generates_unique_keys(self):
        keys = {generate_api_key()[0] for _ in range(10)}
        assert len(keys) == 10


# ---------------------------------------------------------------------------
# API key endpoint tests
# ---------------------------------------------------------------------------


class TestCreateApiKeyEndpoint:
    def test_creates_key_without_admin_key_configured(self):
        mock_db = AsyncMock()
        mock_db.create_api_key = AsyncMock(return_value="key-id-1")

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.post(
                "/api/v1/api-keys",
                json={"name": "Test App", "rate_limit_per_minute": 30},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == "key-id-1"
            assert data["key"].startswith("vs_")
            assert data["name"] == "Test App"
            assert data["rate_limit_per_minute"] == 30

    def test_requires_admin_key_when_configured(self):
        mock_db = AsyncMock()

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            # Set admin key on the app state
            c.app.state.settings.api_admin_key = "secret-admin"

            # No admin header → 401
            resp = c.post("/api/v1/api-keys", json={"name": "Test"})
            assert resp.status_code == 401

            # Wrong admin header → 403
            resp = c.post(
                "/api/v1/api-keys",
                json={"name": "Test"},
                headers={"X-Admin-Key": "wrong"},
            )
            assert resp.status_code == 403

            # Correct admin header → success
            mock_db.create_api_key = AsyncMock(return_value="key-id-2")
            resp = c.post(
                "/api/v1/api-keys",
                json={"name": "Test"},
                headers={"X-Admin-Key": "secret-admin"},
            )
            assert resp.status_code == 200

            # Clean up
            c.app.state.settings.api_admin_key = None


class TestListApiKeysEndpoint:
    def test_lists_keys(self):
        mock_db = AsyncMock()
        mock_db.list_api_keys = AsyncMock(return_value=[
            {
                "id": "k1", "name": "App1", "key_prefix": "vs_abcd1234",
                "is_active": True, "rate_limit_per_minute": 60,
                "created_at": "2025-01-01T00:00:00", "last_used_at": None,
            }
        ])

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/api-keys")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["keys"]) == 1
            assert data["keys"][0]["name"] == "App1"


class TestRevokeApiKeyEndpoint:
    def test_revokes_key(self):
        mock_db = AsyncMock()
        mock_db.deactivate_api_key = AsyncMock(return_value=True)

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.delete("/api/v1/api-keys/key-id-1")
            assert resp.status_code == 200
            assert resp.json()["detail"] == "API key revoked"

    def test_404_for_missing_key(self):
        mock_db = AsyncMock()
        mock_db.deactivate_api_key = AsyncMock(return_value=False)

        with (
            patch("visionscore.api.routes.get_supabase_client", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.delete("/api/v1/api-keys/nonexistent")
            assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth validation tests
# ---------------------------------------------------------------------------


class TestValidateApiKey:
    def test_passes_when_auth_disabled_no_key(self):
        """Requests pass without key when api_auth_enabled=False."""
        with TestClient(app) as c:
            resp = c.get("/api/v1/health")
            assert resp.status_code == 200
