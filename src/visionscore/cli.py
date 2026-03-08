from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from visionscore import __version__
from visionscore.pipeline.metadata import extract_metadata

app = typer.Typer(help="VisionScore - AI-powered photo evaluation tool")
console = Console()


def _parse_weights(weights_str: str) -> AnalysisWeights | None:
    """Parse a 't:a:c:f' weights string into AnalysisWeights, or None on error."""
    from visionscore.config import AnalysisWeights

    parts = weights_str.split(":")
    if len(parts) != 4:
        console.print("[red]Error: --weights must be 4 colon-separated numbers (t:a:c:f)[/red]")
        return None
    try:
        raw = [float(p) for p in parts]
    except ValueError:
        console.print("[red]Error: --weights values must be numbers[/red]")
        return None
    total = sum(raw)
    return AnalysisWeights(
        technical=raw[0] / total,
        aesthetic=raw[1] / total,
        composition=raw[2] / total,
        ai_feedback=raw[3] / total,
    )


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


@app.command()
def analyze(
    image_path: Path = typer.Argument(..., help="Path to the image file"),
    output: str = typer.Option("text", help="Output format: text, json, markdown"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    skip_ai: bool = typer.Option(False, "--skip-ai", help="Skip AI feedback analysis"),
    weights: Optional[str] = typer.Option(
        None, "--weights", help="Custom weights t:a:c:f (e.g. 25:30:25:20)"
    ),
    save: Optional[Path] = typer.Option(None, "--save", help="Save report to file"),
):
    """Analyze a photo and produce quality scores."""
    from visionscore.config import Settings
    from visionscore.output import format_json, format_markdown, render_report
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    settings = Settings()

    if weights:
        parsed = _parse_weights(weights)
        if parsed is None:
            raise typer.Exit(1)
        settings.analysis_weights = parsed

    orchestrator = AnalysisOrchestrator(settings=settings, skip_ai=skip_ai)
    report = orchestrator.run(image_path)

    if verbose:
        console.print(f"[dim]Analysis completed in {report.analysis_time_seconds:.2f}s[/dim]")

    if output == "json":
        content = format_json(report)
        console.print(content)
    elif output == "markdown":
        content = format_markdown(report)
        console.print(content)
    else:
        render_report(report, console, warnings=orchestrator.warnings)

    if save:
        ext = save.suffix.lower()
        if ext == ".md":
            file_content = format_markdown(report)
        else:
            file_content = format_json(report)
        save.write_text(file_content)
        console.print(f"[green]Report saved to {save}[/green]")


@app.command("analyze-batch")
def analyze_batch(
    directory: Path = typer.Argument(..., help="Directory containing images"),
    output: str = typer.Option("text", help="Output format: text, json, csv"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    skip_ai: bool = typer.Option(False, "--skip-ai", help="Skip AI feedback analysis"),
    weights: Optional[str] = typer.Option(
        None, "--weights", help="Custom weights t:a:c:f (e.g. 25:30:25:20)"
    ),
    save: Optional[Path] = typer.Option(None, "--save", help="Save report to file (.csv or .json)"),
):
    """Analyze all images in a directory and produce a comparative summary."""
    import json

    from rich.progress import Progress

    from visionscore.config import Settings
    from visionscore.output import format_csv, render_batch_report
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    if not directory.is_dir():
        console.print(f"[red]Error: '{directory}' is not a directory[/red]")
        raise typer.Exit(1)

    settings = Settings()

    if weights:
        parsed = _parse_weights(weights)
        if parsed is None:
            raise typer.Exit(1)
        settings.analysis_weights = parsed

    orchestrator = AnalysisOrchestrator(settings=settings, skip_ai=skip_ai)

    with Progress(console=console) as progress:
        task = progress.add_task("Analyzing images...", total=None)

        def on_progress(filename: str, current: int, total: int) -> None:
            progress.update(task, total=total, completed=current, description=f"[{current}/{total}] {filename}")

        batch = orchestrator.run_batch(directory, progress_callback=on_progress)

    if verbose:
        console.print(f"[dim]Batch completed in {batch.total_time_seconds:.2f}s[/dim]")

    if batch.total_images == 0:
        console.print("[yellow]No supported images found in directory.[/yellow]")
        return

    if output == "json":
        content = json.dumps(batch.model_dump(mode="json"), indent=2, default=str)
        console.print(content)
    elif output == "csv":
        console.print(format_csv(batch))
    else:
        render_batch_report(batch, console, warnings=orchestrator.warnings)

    if save:
        ext = save.suffix.lower()
        if ext == ".json":
            file_content = json.dumps(batch.model_dump(mode="json"), indent=2, default=str)
        else:
            file_content = format_csv(batch)
        save.write_text(file_content)
        console.print(f"[green]Report saved to {save}[/green]")
