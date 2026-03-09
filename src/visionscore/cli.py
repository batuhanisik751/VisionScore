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


@app.command()
def compare(
    image_a: Path = typer.Argument(..., help="Path to first image (before)"),
    image_b: Path = typer.Argument(..., help="Path to second image (after)"),
    output: str = typer.Option("text", help="Output format: text, json"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    skip_ai: bool = typer.Option(False, "--skip-ai", help="Skip AI feedback analysis"),
    weights: Optional[str] = typer.Option(
        None, "--weights", help="Custom weights t:a:c:f (e.g. 25:30:25:20)"
    ),
    save: Optional[Path] = typer.Option(None, "--save", help="Save comparison report to file"),
):
    """Compare two images and show score differences."""
    from visionscore.config import Settings
    from visionscore.output import (
        build_comparison,
        format_comparison_json,
        render_comparison,
    )
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    for img in (image_a, image_b):
        if not img.is_file():
            console.print(f"[red]Error: '{img}' is not a valid file[/red]")
            raise typer.Exit(1)

    settings = Settings()

    if weights:
        parsed = _parse_weights(weights)
        if parsed is None:
            raise typer.Exit(1)
        settings.analysis_weights = parsed

    orchestrator = AnalysisOrchestrator(settings=settings, skip_ai=skip_ai)

    console.print(f"[dim]Analyzing image A: {image_a.name}...[/dim]")
    report_a = orchestrator.run(image_a)
    console.print(f"[dim]Analyzing image B: {image_b.name}...[/dim]")
    report_b = orchestrator.run(image_b)

    comparison = build_comparison(report_a, report_b)

    if verbose:
        total_time = report_a.analysis_time_seconds + report_b.analysis_time_seconds
        console.print(f"[dim]Comparison completed in {total_time:.2f}s[/dim]")

    if output == "json":
        content = format_comparison_json(comparison)
        console.print(content)
    else:
        render_comparison(comparison, console, warnings=orchestrator.warnings)

    if save:
        file_content = format_comparison_json(comparison)
        save.write_text(file_content)
        console.print(f"[green]Comparison report saved to {save}[/green]")


@app.command()
def train(
    image_dir: Path = typer.Argument(..., help="Directory containing training images"),
    csv_path: Path = typer.Argument(..., help="CSV file with filename,score ratings"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path for fine-tuned weights"
    ),
    base_weights: Optional[Path] = typer.Option(
        None, "--base-weights", help="Base NIMA weights to start from"
    ),
    epochs: int = typer.Option(20, "--epochs", "-e", help="Number of training epochs"),
    batch_size: int = typer.Option(16, "--batch-size", "-b", help="Training batch size"),
    lr: float = typer.Option(1e-4, "--lr", help="Learning rate"),
    val_split: float = typer.Option(0.2, "--val-split", help="Validation split fraction"),
    full: bool = typer.Option(False, "--full", help="Full fine-tuning (unfreeze backbone)"),
    no_augment: bool = typer.Option(False, "--no-augment", help="Disable data augmentation"),
    scale: str = typer.Option(
        "ava", "--scale", help="Rating scale: ava (1-10) or visionscore (0-100)"
    ),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducibility"),
):
    """Fine-tune the NIMA aesthetic model on your own rated image dataset."""
    from visionscore.config import Settings
    from visionscore.training.trainer import NIMAAestheticTrainer, TrainingConfig

    if not image_dir.is_dir():
        console.print(f"[red]Error: '{image_dir}' is not a directory[/red]")
        raise typer.Exit(1)

    if not csv_path.is_file():
        console.print(f"[red]Error: '{csv_path}' is not a valid file[/red]")
        raise typer.Exit(1)

    if scale not in ("ava", "visionscore"):
        console.print("[red]Error: --scale must be 'ava' or 'visionscore'[/red]")
        raise typer.Exit(1)

    settings = Settings()

    resolved_output = output or (settings.model_dir / "nima_finetuned.pth")
    resolved_base = base_weights or (settings.model_dir / "nima_mobilenetv2.pth")

    config = TrainingConfig(
        image_dir=image_dir,
        csv_path=csv_path,
        output_path=resolved_output,
        base_weights=resolved_base if resolved_base.is_file() else None,
        epochs=epochs,
        batch_size=batch_size,
        learning_rate=lr,
        val_split=val_split,
        full_finetune=full,
        augment=not no_augment,
        scale=scale,
        device=settings.device,
        seed=seed,
    )

    trainer = NIMAAestheticTrainer(config, console=console)

    try:
        trainer.train()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("plugins")
def list_plugins():
    """List registered analyzer plugins."""
    from visionscore.config import Settings
    from visionscore.plugins import register_bundled_plugins
    from visionscore.plugins.registry import PluginRegistry

    settings = Settings()
    registry = PluginRegistry()
    registry.discover_entry_points()
    if settings.plugin_dir and settings.plugin_dir.is_dir():
        registry.discover_directory(settings.plugin_dir)
    if settings.enable_bundled_plugins:
        register_bundled_plugins(registry)

    all_plugins = registry.get_all()
    if not all_plugins:
        console.print("[dim]No plugins registered.[/dim]")
        return

    table = Table(title="Registered Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Weight", justify="right")
    table.add_column("Description")

    for info, _cls in all_plugins:
        weight_str = f"{info.score_weight:.2f}" if info.score_weight > 0 else "[dim]none[/dim]"
        table.add_row(info.display_name, info.version, weight_str, info.description)

    console.print(table)
