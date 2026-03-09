"""Tests for GZip compression middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from visionscore.api.app import app
from visionscore.api.supabase_client import reset_supabase_client


@pytest.fixture(autouse=True)
def _reset_sb():
    reset_supabase_client()
    yield
    reset_supabase_client()


class TestGzipMiddleware:
    """Verify GZip middleware compresses large responses."""

    def test_response_works_with_gzip_accept(self):
        """Responses work when client sends Accept-Encoding: gzip."""
        with TestClient(app) as c:
            resp = c.get(
                "/api/v1/health",
                headers={"Accept-Encoding": "gzip"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    def test_response_works_without_gzip_header(self):
        """Responses still work when client doesn't accept gzip."""
        with TestClient(app) as c:
            resp = c.get("/api/v1/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    def test_large_json_response_compressed(self):
        """Large responses get Content-Encoding: gzip when client accepts it."""
        fake_reports = [
            {
                "id": f"report-{i}",
                "image_url": f"http://example.com/img{i}.jpg",
                "overall_score": 75.0 + i,
                "grade": "B",
                "created_at": "2025-01-01T00:00:00",
                "full_report": {"description": "x" * 200},
            }
            for i in range(50)
        ]
        mock_db = AsyncMock()
        mock_db.list_reports = AsyncMock(return_value=(fake_reports, 50))

        with (
            patch("visionscore.api.routes._get_supabase", return_value=mock_db),
            TestClient(app) as c,
        ):
            resp = c.get(
                "/api/v1/reports?limit=50",
                headers={"Accept-Encoding": "gzip"},
            )
            assert resp.status_code == 200
            assert resp.headers.get("content-encoding") == "gzip"
