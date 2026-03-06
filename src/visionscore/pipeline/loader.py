from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass
class LoadedImage:
    original: np.ndarray
    resized: np.ndarray
    path: Path
    format: str
    width: int
    height: int


def load_image(source: str | Path, max_size: int = 1024) -> LoadedImage:
    """Load an image from a file path, validate format, and resize for analysis.

    Images are stored in BGR channel order (cv2 native).
    """
    path = Path(source)

    if not path.exists():
        raise ValueError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format '{path.suffix}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Try cv2 first, fall back to Pillow
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        try:
            pil_image = Image.open(path).convert("RGB")
            image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            raise ValueError(f"Could not load image: {path}") from e

    h, w = image.shape[:2]
    img_format = path.suffix.lstrip(".").upper()
    if img_format == "JPG":
        img_format = "JPEG"

    # Resize if larger than max_size
    scale = max_size / max(h, w)
    if scale < 1.0:
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    else:
        resized = image.copy()

    return LoadedImage(
        original=image,
        resized=resized,
        path=path,
        format=img_format,
        width=w,
        height=h,
    )
