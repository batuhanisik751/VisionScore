from __future__ import annotations

import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
from PIL import Image

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


@dataclass
class LoadedImage:
    original: np.ndarray
    resized: np.ndarray
    path: Path
    format: str
    width: int
    height: int


def _is_url(source: str) -> bool:
    """Check if a source string looks like a URL."""
    try:
        parsed = urlparse(str(source))
        return parsed.scheme in ("http", "https")
    except Exception:
        return False


def _download_image(url: str) -> Path:
    """Download an image URL to a temporary file and return the path."""
    parsed = urlparse(url)
    url_path = parsed.path.lower()

    ext = Path(url_path).suffix
    if not ext or ext not in SUPPORTED_EXTENSIONS:
        ext = ".jpg"

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    try:
        urllib.request.urlretrieve(url, tmp.name)  # noqa: S310
    except Exception as e:
        Path(tmp.name).unlink(missing_ok=True)
        raise ValueError(f"Failed to download image from URL: {url}") from e

    return Path(tmp.name)


def load_image(source: str | Path, max_size: int = 1024) -> LoadedImage:
    """Load an image from a file path or URL, validate format, and resize for analysis.

    Images are stored in BGR channel order (cv2 native).
    """
    downloaded = False

    if isinstance(source, str) and _is_url(source):
        path = _download_image(source)
        downloaded = True
    else:
        path = Path(source)

    if not path.exists():
        raise ValueError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        if downloaded:
            path.unlink(missing_ok=True)
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
            if downloaded:
                path.unlink(missing_ok=True)
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
