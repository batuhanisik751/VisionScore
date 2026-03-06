"""Download NIMA model weights for VisionScore."""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

DEFAULT_MODEL_DIR = Path.home() / ".visionscore" / "models"
NIMA_FILENAME = "nima_mobilenetv2.pth"

# Default URL for NIMA weights trained on AVA dataset.
# Replace with your own hosted weights URL.
DEFAULT_NIMA_URL = ""

EXPECTED_SHA256 = ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _progress_hook(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(100, downloaded * 100 // total_size)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        print(f"\r  Downloading: {mb:.1f}/{total_mb:.1f} MB ({pct}%)", end="", flush=True)


def download_nima_weights(
    url: str = DEFAULT_NIMA_URL,
    dest_dir: Path = DEFAULT_MODEL_DIR,
    expected_sha256: str = EXPECTED_SHA256,
    force: bool = False,
) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / NIMA_FILENAME

    if dest_path.exists() and not force:
        print(f"Model already exists: {dest_path}")
        return dest_path

    if not url:
        print("No download URL configured.")
        print("Creating model with ImageNet-pretrained backbone (not AVA-trained).")
        print("Aesthetic scores will not be meaningful until AVA-trained weights are provided.")
        return _create_backbone_only(dest_path)

    print(f"Downloading NIMA weights from: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path, reporthook=_progress_hook)
        print()  # newline after progress bar
    except Exception as e:
        print(f"\nDownload failed: {e}")
        print("Falling back to ImageNet-pretrained backbone.")
        return _create_backbone_only(dest_path)

    if expected_sha256:
        actual = _sha256(dest_path)
        if actual != expected_sha256:
            dest_path.unlink()
            print(f"Checksum mismatch! Expected {expected_sha256[:16]}..., got {actual[:16]}...")
            sys.exit(1)
        print("Checksum verified.")

    print(f"Model saved to: {dest_path}")
    return dest_path


def _create_backbone_only(dest_path: Path) -> Path:
    try:
        import torch
        import torch.nn as nn
        from torchvision import models

        base = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)
        base.classifier = nn.Sequential(
            nn.Dropout(p=0.75),
            nn.Linear(1280, 10),
            nn.Softmax(dim=1),
        )
        torch.save(base.state_dict(), dest_path)
        print(f"Backbone-only model saved to: {dest_path}")
        return dest_path
    except ImportError:
        print("PyTorch not installed. Cannot create backbone model.")
        print("Install with: pip install torch torchvision")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NIMA model weights")
    parser.add_argument("--url", default=DEFAULT_NIMA_URL, help="URL to download weights from")
    parser.add_argument("--dir", type=Path, default=DEFAULT_MODEL_DIR, help="Model directory")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    download_nima_weights(url=args.url, dest_dir=args.dir, force=args.force)


if __name__ == "__main__":
    main()
