from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageFilter


@pytest.fixture(scope="session")
def image_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("images")


@pytest.fixture(scope="session")
def sharp_image_path(image_dir: Path) -> Path:
    """200x200 checkerboard pattern with high-contrast edges."""
    img = Image.new("RGB", (200, 200))
    pixels = img.load()
    for y in range(200):
        for x in range(200):
            color = (255, 255, 255) if (x // 10 + y // 10) % 2 == 0 else (0, 0, 0)
            pixels[x, y] = color
    path = image_dir / "sharp.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def blurry_image_path(image_dir: Path) -> Path:
    """200x200 blurred checkerboard."""
    img = Image.new("RGB", (200, 200))
    pixels = img.load()
    for y in range(200):
        for x in range(200):
            color = (255, 255, 255) if (x // 10 + y // 10) % 2 == 0 else (0, 0, 0)
            pixels[x, y] = color
    img = img.filter(ImageFilter.GaussianBlur(radius=5))
    path = image_dir / "blurry.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def bright_image_path(image_dir: Path) -> Path:
    """200x200 near-white image."""
    img = Image.new("RGB", (200, 200), (240, 240, 240))
    path = image_dir / "bright.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def dark_image_path(image_dir: Path) -> Path:
    """200x200 near-black image."""
    img = Image.new("RGB", (200, 200), (15, 15, 15))
    path = image_dir / "dark.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def normal_image_path(image_dir: Path) -> Path:
    """200x200 horizontal gradient with normal exposure."""
    img = Image.new("RGB", (200, 200))
    pixels = img.load()
    for y in range(200):
        for x in range(200):
            v = int(255 * x / 199)
            pixels[x, y] = (v, v, v)
    path = image_dir / "normal.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def large_image_path(image_dir: Path) -> Path:
    """2048x2048 image for resize testing."""
    img = Image.new("RGB", (2048, 2048), (100, 150, 200))
    path = image_dir / "large.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def wide_image_path(image_dir: Path) -> Path:
    """2000x1000 image for aspect ratio testing."""
    img = Image.new("RGB", (2000, 1000), (100, 150, 200))
    path = image_dir / "wide.jpg"
    img.save(path, "JPEG")
    return path


@pytest.fixture(scope="session")
def noisy_image_path(image_dir: Path) -> Path:
    """200x200 mid-gray image with heavy Gaussian noise."""
    import numpy as np

    rng = np.random.default_rng(42)
    base = np.full((200, 200, 3), 128, dtype=np.uint8)
    noise = rng.normal(0, 40, base.shape).astype(np.int16)
    noisy = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(noisy)
    path = image_dir / "noisy.jpg"
    img.save(path, "JPEG", quality=95)
    return path


@pytest.fixture(scope="session")
def flat_gray_image_path(image_dir: Path) -> Path:
    """200x200 uniform mid-gray image (zero dynamic range)."""
    img = Image.new("RGB", (200, 200), (128, 128, 128))
    path = image_dir / "flat_gray.jpg"
    img.save(path, "JPEG")
    return path
