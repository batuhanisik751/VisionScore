from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from visionscore import __version__
from visionscore.api.supabase_client import reset_supabase_client
from visionscore.models import (
    AnalysisReport,
    CompositionScore,
    Grade,
    ImageMeta,
    TechnicalScore,
)


@pytest.fixture(autouse=True)
def _reset_sb():
    reset_supabase_client()
    yield
    reset_supabase_client()


@pytest.fixture
def mock_report() -> AnalysisReport:
    return AnalysisReport(
        image_meta=ImageMeta(
            path="test.jpg", width=200, height=200, format="JPEG"
        ),
        technical=TechnicalScore(
            sharpness=80, exposure=70, noise=60, dynamic_range=75, overall=71
        ),
        composition=CompositionScore(
            rule_of_thirds=80,
            subject_position=70,
            horizon=75,
            balance=65,
            overall=73,
        ),
        overall_score=72.5,
        grade=Grade.B,
    )


@pytest.fixture
def jpeg_bytes() -> bytes:
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def client(mock_report):
    with patch(
        "visionscore.pipeline.orchestrator.AnalysisOrchestrator"
    ) as MockOrch, patch(
        "visionscore.api.routes.get_supabase_client", return_value=None
    ):
        instance = MagicMock()
        instance.run.return_value = mock_report
        instance.warnings = []
        MockOrch.return_value = instance

        from visionscore.api.app import app

        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == __version__
        assert data["supabase_connected"] is False


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


class TestAnalyze:
    def test_valid_jpeg(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert data["report"]["overall_score"] == 72.5
        assert data["report"]["grade"] == "B"

    def test_invalid_extension(self, client):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("document.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 400
        assert "Unsupported format" in resp.json()["detail"]

    def test_empty_file(self, client):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("photo.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_skip_ai_param(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze?skip_ai=true",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200

    def test_weights_param(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze?weights=30:30:30:10",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200

    def test_png_accepted(self, client):
        img = Image.new("RGB", (50, 50), (100, 100, 100))
        buf = io.BytesIO()
        img.save(buf, "PNG")
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("photo.png", buf.getvalue(), "image/png")},
        )
        assert resp.status_code == 200

    def test_no_filename_returns_error(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Analyze + Save
# ---------------------------------------------------------------------------


class TestAnalyzeAndSave:
    def test_returns_503_without_supabase(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze/save",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 503

    def test_saves_with_mocked_supabase(self, jpeg_bytes, mock_report):
        mock_sb = MagicMock()
        mock_sb.upload_image = AsyncMock(return_value="https://img.url/photo.jpg")
        mock_sb.save_report = AsyncMock(return_value="report-id-123")

        with patch(
            "visionscore.pipeline.orchestrator.AnalysisOrchestrator"
        ) as MockOrch, patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            instance = MagicMock()
            instance.run.return_value = mock_report
            instance.warnings = []
            MockOrch.return_value = instance

            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.post(
                    "/api/v1/analyze/save",
                    files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "report-id-123"
        assert data["image_url"] == "https://img.url/photo.jpg"


# ---------------------------------------------------------------------------
# Reports CRUD
# ---------------------------------------------------------------------------


class TestReportsCRUD:
    def test_list_returns_503_without_supabase(self, client):
        resp = client.get("/api/v1/reports")
        assert resp.status_code == 503

    def test_get_returns_503_without_supabase(self, client):
        resp = client.get("/api/v1/reports/some-id")
        assert resp.status_code == 503

    def test_delete_returns_503_without_supabase(self, client):
        resp = client.delete("/api/v1/reports/some-id")
        assert resp.status_code == 503

    def test_list_reports_with_mocked_supabase(self):
        mock_sb = MagicMock()
        mock_sb.list_reports = AsyncMock(
            return_value=([{"id": "1"}, {"id": "2"}], 2)
        )

        with patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.get("/api/v1/reports?limit=10&offset=0")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reports"]) == 2
        assert data["total"] == 2

    def test_get_report_found(self):
        mock_sb = MagicMock()
        mock_sb.get_report = AsyncMock(
            return_value={"id": "abc", "overall_score": 75}
        )

        with patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.get("/api/v1/reports/abc")

        assert resp.status_code == 200
        assert resp.json()["id"] == "abc"

    def test_get_report_not_found(self):
        mock_sb = MagicMock()
        mock_sb.get_report = AsyncMock(return_value=None)

        with patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.get("/api/v1/reports/nonexistent")

        assert resp.status_code == 404

    def test_delete_report_success(self):
        mock_sb = MagicMock()
        mock_sb.delete_report = AsyncMock(return_value=True)

        with patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.delete("/api/v1/reports/abc")

        assert resp.status_code == 200

    def test_delete_report_not_found(self):
        mock_sb = MagicMock()
        mock_sb.delete_report = AsyncMock(return_value=False)

        with patch(
            "visionscore.api.routes.get_supabase_client", return_value=mock_sb
        ):
            from visionscore.api.app import app

            with TestClient(app) as c:
                resp = c.delete("/api/v1/reports/nonexistent")

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORS:
    def test_cors_headers(self, client):
        resp = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") is not None
