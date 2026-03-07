#!/usr/bin/env python3
"""Demo script that generates sample images and analyzes them with VisionScore.

Usage:
    python examples/demo.py
    python examples/demo.py --save-reports
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from rich.console import Console

console = Console()


def generate_sample_images(output_dir: Path) -> list[tuple[str, Path]]:
    """Generate a set of sample images with varying quality characteristics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    samples: list[tuple[str, Path]] = []

    # 1. Well-composed landscape-style image
    img = Image.new("RGB", (800, 600))
    pixels = img.load()
    for y in range(600):
        for x in range(800):
            if y < 250:
                # Sky gradient
                r = 100 + int(80 * (1 - y / 250))
                g = 150 + int(80 * (1 - y / 250))
                b = 200 + int(55 * (1 - y / 250))
            else:
                # Ground
                r = 60 + int(40 * ((y - 250) / 350))
                g = 120 - int(40 * ((y - 250) / 350))
                b = 50
            pixels[x, y] = (min(r, 255), min(g, 255), min(b, 255))
    path = output_dir / "landscape.jpg"
    img.save(path, "JPEG", quality=95)
    samples.append(("Well-exposed landscape", path))

    # 2. Subject at power point (good composition)
    img = Image.new("RGB", (600, 600), (30, 30, 50))
    draw = ImageDraw.Draw(img)
    # Bright circle at top-left power point (1/3, 1/3)
    cx, cy = 200, 200
    draw.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], fill=(255, 220, 180))
    # Some background texture
    for i in range(0, 600, 40):
        draw.line([(0, i), (600, i)], fill=(40, 40, 60), width=1)
    path = output_dir / "good_composition.jpg"
    img.save(path, "JPEG", quality=95)
    samples.append(("Good composition (power point)", path))

    # 3. Overexposed image
    img = Image.new("RGB", (400, 400), (250, 250, 250))
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 350, 350], fill=(255, 255, 255))
    draw.ellipse([150, 150, 250, 250], fill=(240, 240, 240))
    path = output_dir / "overexposed.jpg"
    img.save(path, "JPEG", quality=90)
    samples.append(("Overexposed image", path))

    # 4. Blurry image
    img = Image.new("RGB", (400, 400))
    pixels = img.load()
    for y in range(400):
        for x in range(400):
            color = (200, 100, 50) if (x // 20 + y // 20) % 2 == 0 else (50, 100, 200)
            pixels[x, y] = color
    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    path = output_dir / "blurry.jpg"
    img.save(path, "JPEG", quality=90)
    samples.append(("Blurry image", path))

    # 5. High-contrast sharp image
    img = Image.new("RGB", (600, 400))
    pixels = img.load()
    for y in range(400):
        for x in range(600):
            v = int(255 * x / 599)
            pixels[x, y] = (v, v, v)
    path = output_dir / "gradient.jpg"
    img.save(path, "JPEG", quality=95)
    samples.append(("Full-range gradient (sharp)", path))

    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="VisionScore demo")
    parser.add_argument(
        "--save-reports",
        action="store_true",
        help="Save JSON reports to examples/reports/",
    )
    args = parser.parse_args()

    examples_dir = Path(__file__).parent
    images_dir = examples_dir / "sample_images"
    reports_dir = examples_dir / "reports"

    console.print("[bold]VisionScore Demo[/bold]")
    console.print("Generating sample images...\n")

    samples = generate_sample_images(images_dir)

    from visionscore.config import Settings
    from visionscore.output import format_json, render_report
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    settings = Settings()
    orchestrator = AnalysisOrchestrator(settings=settings, skip_ai=True)

    for description, image_path in samples:
        console.print(f"\n[bold cyan]--- {description} ---[/bold cyan]")
        console.print(f"[dim]{image_path}[/dim]\n")

        report = orchestrator.run(image_path)
        render_report(report, console, warnings=orchestrator.warnings)

        if args.save_reports:
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"{image_path.stem}.json"
            report_path.write_text(format_json(report))
            console.print(f"[green]Report saved: {report_path}[/green]")


if __name__ == "__main__":
    main()
