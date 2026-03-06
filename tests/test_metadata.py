from __future__ import annotations

from pathlib import Path

from visionscore.pipeline.metadata import extract_metadata


def test_extract_metadata_basic(normal_image_path: Path):
    meta = extract_metadata(normal_image_path)
    assert meta.width == 200
    assert meta.height == 200
    assert meta.format == "JPEG"
    assert str(normal_image_path) in meta.path


def test_extract_metadata_no_exif(normal_image_path: Path):
    """Synthetic images have no EXIF — should return empty dict gracefully."""
    meta = extract_metadata(normal_image_path)
    assert isinstance(meta.exif, dict)
    assert len(meta.exif) == 0
