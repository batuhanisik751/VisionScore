"""Thumbnail generation for mobile-optimized image delivery."""

from __future__ import annotations

import io

from PIL import Image


def generate_thumbnail(
    image_bytes: bytes,
    max_width: int = 400,
    quality: int = 75,
) -> bytes:
    """Resize an image to fit within *max_width*, preserving aspect ratio.

    Returns JPEG bytes.
    """
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
