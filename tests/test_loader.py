from __future__ import annotations

from pathlib import Path

import pytest

from visionscore.pipeline.loader import load_image


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
