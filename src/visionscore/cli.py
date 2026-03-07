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

    # Aesthetic analysis (graceful degradation if weights missing)
    aesthetic = None
    try:
        from visionscore.analyzers.aesthetic import AestheticAnalyzer

        model_path = settings.model_dir / "nima_mobilenetv2.pth"
        aes_analyzer = AestheticAnalyzer(model_path=model_path, device=settings.device)
        aesthetic = aes_analyzer.analyze(image, metadata=meta)
    except FileNotFoundError:
        pass  # warning printed after tables
    except Exception as e:
        if verbose:
            console.print(f"[dim]Aesthetic scoring error: {e}[/dim]")

    # Composition analysis
    from visionscore.analyzers.composition import CompositionAnalyzer

    comp_analyzer = CompositionAnalyzer()
    composition = comp_analyzer.analyze(image, metadata=meta)

    # AI Feedback (graceful degradation if Ollama not running)
    ai_feedback = None
    try:
        from visionscore.analyzers.ai_feedback import AIFeedbackAnalyzer

        ai_analyzer = AIFeedbackAnalyzer(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
        ai_feedback = ai_analyzer.analyze(image, metadata=meta)
    except ConnectionError:
        pass  # warning printed after tables
    except Exception as e:
        if verbose:
            console.print(f"[dim]AI feedback error: {e}[/dim]")

    if output == "json":
        import json

        data = {"technical": tech.model_dump(), "composition": composition.model_dump()}
        if aesthetic:
            data["aesthetic"] = aesthetic.model_dump()
        if ai_feedback:
            data["ai_feedback"] = ai_feedback.model_dump()
        console.print(json.dumps(data, indent=2))
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

    if aesthetic:
        aes_table = Table(title="Aesthetic Quality")
        aes_table.add_column("Metric", style="cyan")
        aes_table.add_column("Score", style="white", justify="right")
        aes_table.add_column("Bar", style="white")

        nc = (
            "green" if aesthetic.nima_score >= 70
            else "yellow" if aesthetic.nima_score >= 40
            else "red"
        )
        aes_table.add_row(
            "NIMA Score",
            f"[{nc}]{aesthetic.nima_score:.1f}[/{nc}]",
            _score_bar(aesthetic.nima_score),
        )
        aes_table.add_row("Confidence", f"{aesthetic.confidence:.2f}", "")
        aes_table.add_row("Std Dev", f"{aesthetic.std_dev:.2f}", "")
        aes_table.add_section()
        ac = (
            "green" if aesthetic.overall >= 70
            else "yellow" if aesthetic.overall >= 40
            else "red"
        )
        aes_table.add_row(
            "[bold]Overall[/bold]",
            f"[bold {ac}]{aesthetic.overall:.1f}[/bold {ac}]",
            _score_bar(aesthetic.overall),
        )
        console.print(aes_table)
    else:
        console.print(
            "[yellow]Aesthetic scoring skipped: NIMA weights not found. "
            "Run: python scripts/download_models.py[/yellow]"
        )

    comp_table = Table(title="Composition")
    comp_table.add_column("Metric", style="cyan")
    comp_table.add_column("Score", style="white", justify="right")
    comp_table.add_column("Bar", style="white")

    for field, label in [
        ("rule_of_thirds", "Rule of Thirds"),
        ("subject_position", "Subject Position"),
        ("horizon", "Horizon"),
        ("balance", "Balance"),
    ]:
        score = getattr(composition, field)
        color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
        comp_table.add_row(label, f"[{color}]{score:.1f}[/{color}]", _score_bar(score))

    comp_table.add_section()
    cc = (
        "green" if composition.overall >= 70
        else "yellow" if composition.overall >= 40
        else "red"
    )
    comp_table.add_row(
        "[bold]Overall[/bold]",
        f"[bold {cc}]{composition.overall:.1f}[/bold {cc}]",
        _score_bar(composition.overall),
    )
    console.print(comp_table)

    if ai_feedback:
        ai_table = Table(title="AI Feedback")
        ai_table.add_column("Field", style="cyan")
        ai_table.add_column("Value", style="white")

        ai_table.add_row("Genre", ai_feedback.genre)
        ai_table.add_row("Description", ai_feedback.description)
        ai_table.add_row("Mood", ai_feedback.mood)

        sc = "green" if ai_feedback.score >= 70 else "yellow" if ai_feedback.score >= 40 else "red"
        ai_table.add_row("Score", f"[{sc}]{ai_feedback.score:.1f}[/{sc}]  {_score_bar(ai_feedback.score)}")

        ai_table.add_section()
        for s in ai_feedback.strengths:
            ai_table.add_row("[green]+[/green] Strength", s)
        for imp in ai_feedback.improvements:
            ai_table.add_row("[yellow]>[/yellow] Improve", imp)

        ai_table.add_section()
        ai_table.add_row("Reasoning", ai_feedback.reasoning)
        console.print(ai_table)
    else:
        console.print(
            "[yellow]AI feedback skipped: Ollama not available. "
            "Run: ollama serve && ollama pull llava[/yellow]"
        )
