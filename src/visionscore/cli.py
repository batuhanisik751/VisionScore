from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from visionscore import __version__
from visionscore.pipeline.loader import load_image
from visionscore.pipeline.metadata import extract_metadata

app = typer.Typer(help="VisionScore - AI-powered photo evaluation tool")
console = Console()


@app.command()
def version():
    """Print the VisionScore version."""
    console.print(f"VisionScore v{__version__}")


@app.command()
def info(
    image_path: Path = typer.Argument(..., help="Path to the image file"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """Display image metadata and EXIF information."""
    meta = extract_metadata(image_path)

    if output_json:
        console.print(meta.model_dump_json(indent=2))
        return

    table = Table(title=f"Image Info: {image_path.name}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Path", meta.path)
    table.add_row("Dimensions", f"{meta.width} x {meta.height}")
    table.add_row("Format", meta.format)

    if meta.exif:
        table.add_section()
        for key, value in meta.exif.items():
            table.add_row(key.replace("_", " ").title(), str(value))
    else:
        table.add_section()
        table.add_row("EXIF", "No EXIF data found")

    console.print(table)


def _score_bar(score: float, width: int = 20) -> str:
    """Generate a colored progress bar string for a score 0-100."""
    filled = int(score / 100 * width)
    empty = width - filled
    color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    return f"[{color}]{'█' * filled}[/{color}]{'░' * empty}"


@app.command()
def analyze(
    image_path: Path = typer.Argument(..., help="Path to the image file"),
    output: str = typer.Option("text", help="Output format: text, json, markdown"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Analyze a photo and produce quality scores."""
    from visionscore.analyzers.technical import TechnicalAnalyzer
    from visionscore.config import Settings

    settings = Settings()
    image = load_image(image_path, max_size=settings.max_image_size)
    meta = extract_metadata(image_path)

    console.print(f"[bold]VisionScore Analysis[/bold]: {image_path.name}")
    console.print(f"Dimensions: {meta.width} x {meta.height} | Format: {meta.format}")
    console.print()

    tech_analyzer = TechnicalAnalyzer(thresholds=settings.thresholds)
    tech = tech_analyzer.analyze(image, metadata=meta)

    if output == "json":
        console.print(tech.model_dump_json(indent=2))
        return

    table = Table(title="Technical Quality")
    table.add_column("Metric", style="cyan")
    table.add_column("Score", style="white", justify="right")
    table.add_column("Bar", style="white")

    for field, label in [
        ("sharpness", "Sharpness"),
        ("exposure", "Exposure"),
        ("noise", "Noise Level"),
        ("dynamic_range", "Dynamic Range"),
    ]:
        score = getattr(tech, field)
        color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
        table.add_row(label, f"[{color}]{score:.1f}[/{color}]", _score_bar(score))

    table.add_section()
    oc = "green" if tech.overall >= 70 else "yellow" if tech.overall >= 40 else "red"
    table.add_row(
        "[bold]Overall[/bold]",
        f"[bold {oc}]{tech.overall:.1f}[/bold {oc}]",
        _score_bar(tech.overall),
    )
    console.print(table)
