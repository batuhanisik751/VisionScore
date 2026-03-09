from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

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
        image_meta=ImageMeta(path="test.jpg", width=200, height=200, format="JPEG"),
        technical=TechnicalScore(sharpness=80, exposure=70, noise=60, dynamic_range=75, overall=71),
        composition=CompositionScore(
            rule_of_thirds=80, subject_position=70, horizon=75, balance=65, overall=73,
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
    with (
        patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator") as MockOrch,
        patch("visionscore.api.routes.get_supabase_client", return_value=None),
    ):
        instance = MagicMock()

        def _fake_run(path, progress_callback=None):
            if progress_callback:
                progress_callback("loading", 1, 9, "Loading image...")
                progress_callback("metadata", 2, 9, "Extracting metadata...")
                progress_callback("technical", 3, 9, "Running technical analysis...")
                progress_callback("aesthetic", 4, 9, "Running aesthetic analysis...")
                progress_callback("composition", 5, 9, "Running composition analysis...")
                progress_callback("ai_feedback", 6, 9, "Running AI feedback analysis...")
                progress_callback("suggestions", 7, 9, "Generating improvement suggestions...")
                progress_callback("plugins", 8, 9, "Running plugin analyzers...")
                progress_callback("aggregating", 9, 9, "Aggregating scores and grading...")
            return mock_report

        instance.run.side_effect = _fake_run
        instance.warnings = []
        MockOrch.return_value = instance

        from visionscore.api.app import app

        with TestClient(app) as c:
            yield c


def _upload(client, jpeg_bytes, **params) -> dict:
    """Helper: upload a JPEG and return the JSON response."""
    resp = client.post(
        "/api/v1/analyze/upload",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        params=params,
    )
    return resp


def _parse_sse_events(text: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts."""
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_type = "message"
        data = ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        if data:
            events.append({"event": event_type, "data": json.loads(data)})
    return events


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


class TestUploadEndpoint:
    def test_returns_task_id(self, client, jpeg_bytes):
        resp = _upload(client, jpeg_bytes)
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert isinstance(data["task_id"], str)
        assert len(data["task_id"]) == 32  # uuid hex

    def test_invalid_extension(self, client):
        resp = client.post(
            "/api/v1/analyze/upload",
            files={"file": ("file.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400

    def test_empty_file(self, client):
        resp = client.post(
            "/api/v1/analyze/upload",
            files={"file": ("photo.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_preserves_query_params(self, client, jpeg_bytes):
        resp = _upload(client, jpeg_bytes, skip_ai="true", weights="30:30:30:10")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Stream endpoint
# ---------------------------------------------------------------------------


class TestStreamEndpoint:
    def test_unknown_task_id(self, client):
        resp = client.get("/api/v1/analyze/stream/nonexistent")
        assert resp.status_code == 404

    def test_content_type(self, client, jpeg_bytes):
        task_id = _upload(client, jpeg_bytes).json()["task_id"]
        resp = client.get(f"/api/v1/analyze/stream/{task_id}")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_progress_events_in_order(self, client, jpeg_bytes):
        task_id = _upload(client, jpeg_bytes).json()["task_id"]
        resp = client.get(f"/api/v1/analyze/stream/{task_id}")
        events = _parse_sse_events(resp.text)

        progress_events = [e for e in events if e["event"] == "progress"]
        assert len(progress_events) == 9

        # Verify order
        for i, evt in enumerate(progress_events):
            assert evt["data"]["stage_index"] == i + 1
            assert evt["data"]["total_stages"] == 9
            assert "message" in evt["data"]
            assert "percent" in evt["data"]

    def test_complete_event_has_report(self, client, jpeg_bytes):
        task_id = _upload(client, jpeg_bytes).json()["task_id"]
        resp = client.get(f"/api/v1/analyze/stream/{task_id}")
        events = _parse_sse_events(resp.text)

        complete_events = [e for e in events if e["event"] == "complete"]
        assert len(complete_events) == 1
        data = complete_events[0]["data"]
        assert "report" in data
        assert "warnings" in data
        assert data["report"]["overall_score"] == 72.5

    def test_task_consumed_once(self, client, jpeg_bytes):
        task_id = _upload(client, jpeg_bytes).json()["task_id"]
        # First request consumes the task
        resp1 = client.get(f"/api/v1/analyze/stream/{task_id}")
        assert resp1.status_code == 200
        # Second request fails
        resp2 = client.get(f"/api/v1/analyze/stream/{task_id}")
        assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# Regression: existing endpoint still works
# ---------------------------------------------------------------------------


class TestExistingAnalyzeUnchanged:
    def test_post_analyze_still_works(self, client, jpeg_bytes):
        resp = client.post(
            "/api/v1/analyze",
            files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "report" in data
        assert data["report"]["overall_score"] == 72.5
