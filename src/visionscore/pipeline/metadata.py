from __future__ import annotations

from pathlib import Path

import exifread
from PIL import Image

from visionscore.models import ImageMeta

# EXIF tag mappings: friendly name -> exifread tag key
_EXIF_FIELDS = {
    "camera_make": "Image Make",
    "camera_model": "Image Model",
    "lens": "EXIF LensModel",
    "iso": "EXIF ISOSpeedRatings",
    "aperture": "EXIF FNumber",
    "shutter_speed": "EXIF ExposureTime",
    "focal_length": "EXIF FocalLength",
    "date_taken": "EXIF DateTimeOriginal",
}


def extract_metadata(image_path: str | Path) -> ImageMeta:
    """Extract image metadata including dimensions, format, and EXIF data."""
    path = Path(image_path)

    # Get dimensions and format from Pillow (reliable for all formats)
    try:
        with Image.open(path) as img:
            width, height = img.size
            img_format = img.format or ""
    except Exception:
        width, height = 0, 0
        img_format = ""

    # Extract EXIF with exifread
    exif: dict[str, str] = {}
    try:
        with open(path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        for friendly_name, tag_key in _EXIF_FIELDS.items():
            if tag_key in tags:
                exif[friendly_name] = str(tags[tag_key])
    except Exception:
        pass  # Gracefully handle corrupt/missing EXIF

    return ImageMeta(
        path=str(path),
        width=width,
        height=height,
        format=img_format,
        exif=exif,
    )
