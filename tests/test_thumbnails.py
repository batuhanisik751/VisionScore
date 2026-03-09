"""Tests for thumbnail generation module and endpoint."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from visionscore.api.app import app
from visionscore.api.supabase_client import reset_supabase_client
from visionscore.api.thumbnails import generate_thumbnail


@pytest.fixture(autouse=True)
def _reset_sb():
    reset_supabase_client()
    yield
    reset_supabase_client()


def _make_image(width: int, height: int, fmt: str = "JPEG") -> bytes:
    """Create a test image of the given size."""
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# ---------- Unit tests for generate_thumbnail ----------


class TestGenerateThumbnail:
    def test_produces_smaller_image(self):
        raw = _make_image(1200, 800)
        thumb = generate_thumbnail(raw, max_width=400)
        img = Image.open(io.BytesIO(thumb))
        assert img.width == 400
        assert len(thumb) < len(raw)

    def test_maintains_aspect_ratio(self):
        raw = _make_image(1000, 500)
        thumb = generate_thumbnail(raw, max_width=200)
        img = Image.open(io.BytesIO(thumb))
        assert img.width == 200
        assert img.height == 100  # 500 * (200/1000)

    def test_respects_max_width_param(self):
        raw = _make_image(800, 600)
        thumb = generate_thumbnail(raw, max_width=300)
        img = Image.open(io.BytesIO(thumb))
        assert img.width == 300

    def test_no_upscale_for_small_images(self):
        raw = _make_image(200, 150)
        thumb = generate_thumbnail(raw, max_width=400)
        img = Image.open(io.BytesIO(thumb))
        assert img.width == 200
        assert img.height == 150

    def test_handles_rgba_input(self):
        img = Image.new("RGBA", (800, 600), color=(255, 0, 0, 128))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        raw = buf.getvalue()
        thumb = generate_thumbnail(raw, max_width=400)
        result = Image.open(io.BytesIO(thumb))
        assert result.mode == "RGB"
        assert result.width == 400

    def test_quality_param_affects_size(self):
        raw = _make_image(800, 600)
        high_q = generate_thumbnail(raw, max_width=400, quality=95)
        low_q = generate_thumbnail(raw, max_width=400, quality=20)
        assert len(low_q) < len(high_q)


# ---------- Endpoint tests ----------


class TestThumbnailEndpoint:
    def test_returns_thumbnail_for_existing_upload(self, tmp_path: Path):
        img_bytes = _make_image(1000, 800)
        img_file = tmp_path / "test_img.jpg"
        img_file.write_bytes(img_bytes)

        with (
            patch("visionscore.api.routes.UPLOADS_DIR", tmp_path),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/uploads/test_img.jpg/thumbnail")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "image/jpeg"
            result = Image.open(io.BytesIO(resp.content))
            assert result.width == 400

    def test_404_for_missing_image(self, tmp_path: Path):
        with (
            patch("visionscore.api.routes.UPLOADS_DIR", tmp_path),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/uploads/nonexistent.jpg/thumbnail")
            assert resp.status_code == 404

    def test_custom_width_param(self, tmp_path: Path):
        img_bytes = _make_image(1000, 800)
        img_file = tmp_path / "wide.jpg"
        img_file.write_bytes(img_bytes)

        with (
            patch("visionscore.api.routes.UPLOADS_DIR", tmp_path),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/uploads/wide.jpg/thumbnail?width=200")
            assert resp.status_code == 200
            result = Image.open(io.BytesIO(resp.content))
            assert result.width == 200

    def test_path_traversal_blocked(self, tmp_path: Path):
        with (
            patch("visionscore.api.routes.UPLOADS_DIR", tmp_path),
            TestClient(app) as c,
        ):
            resp = c.get("/api/v1/uploads/..%2F..%2Fetc%2Fpasswd/thumbnail")
            assert resp.status_code == 404
