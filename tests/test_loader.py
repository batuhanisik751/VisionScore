from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from visionscore.pipeline.loader import (
    SUPPORTED_EXTENSIONS,
    _download_image,
    _is_url,
    load_image,
)


def test_load_valid_jpeg(normal_image_path: Path):
    result = load_image(normal_image_path)
    assert result.width == 200
    assert result.height == 200
    assert result.format == "JPEG"
    assert result.original.shape == (200, 200, 3)


def test_load_resizes_large_image(large_image_path: Path):
    result = load_image(large_image_path, max_size=1024)
    assert result.resized.shape[0] == 1024
    assert result.resized.shape[1] == 1024
    # Original preserved
    assert result.original.shape[0] == 2048


def test_load_preserves_aspect_ratio(wide_image_path: Path):
    result = load_image(wide_image_path, max_size=1024)
    rh, rw = result.resized.shape[:2]
    assert rw == 1024
    assert rh == 512


def test_load_invalid_path():
    with pytest.raises(ValueError, match="File not found"):
        load_image("/nonexistent/photo.jpg")


def test_load_invalid_format(tmp_path: Path):
    bad_file = tmp_path / "notes.txt"
    bad_file.write_text("not an image")
    with pytest.raises(ValueError, match="Unsupported format"):
        load_image(bad_file)


# --- URL loading tests ---


def test_is_url_http():
    assert _is_url("http://example.com/photo.jpg") is True


def test_is_url_https():
    assert _is_url("https://example.com/photo.png") is True


def test_is_url_file_path():
    assert _is_url("/home/user/photo.jpg") is False


def test_is_url_relative_path():
    assert _is_url("photos/test.jpg") is False


def test_load_image_from_url(tmp_path: Path):
    """Test that load_image handles a URL by downloading first."""
    # Create a real image file to serve as the "downloaded" result
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img_path = tmp_path / "downloaded.jpg"
    cv2.imwrite(str(img_path), img)

    with patch("visionscore.pipeline.loader._download_image", return_value=img_path):
        result = load_image("https://example.com/photo.jpg")
        assert result.width == 100
        assert result.height == 100
        assert result.format == "JPEG"


def test_download_image_failure():
    """Test that _download_image raises ValueError on network error."""
    with patch(
        "visionscore.pipeline.loader.urllib.request.urlretrieve",
        side_effect=OSError("connection refused"),
    ):
        with pytest.raises(ValueError, match="Failed to download"):
            _download_image("https://example.com/missing.jpg")


# --- HEIC/HEIF removed ---


def test_heic_not_in_supported_extensions():
    assert ".heic" not in SUPPORTED_EXTENSIONS


def test_heif_not_in_supported_extensions():
    assert ".heif" not in SUPPORTED_EXTENSIONS


def test_heic_extension_rejected(tmp_path: Path):
    """Verify .heic files are rejected as unsupported."""
    heic_file = tmp_path / "photo.heic"
    heic_file.write_bytes(b"\x00" * 16)
    with pytest.raises(ValueError, match="Unsupported format"):
        load_image(heic_file)
