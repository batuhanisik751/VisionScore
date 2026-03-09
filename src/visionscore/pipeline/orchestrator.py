from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from visionscore.config import Settings
from visionscore.models import AnalysisReport, BatchImageResult, BatchResult
from visionscore.pipeline.loader import SUPPORTED_EXTENSIONS, load_image
from visionscore.pipeline.metadata import extract_metadata
from visionscore.scoring.aggregator import ScoreAggregator
from visionscore.scoring.grading import assign_grade


_STAGES: list[tuple[str, str]] = [
    ("loading", "Loading image..."),
    ("metadata", "Extracting metadata..."),
    ("technical", "Running technical analysis..."),
    ("aesthetic", "Running aesthetic analysis..."),
    ("composition", "Running composition analysis..."),
    ("ai_feedback", "Running AI feedback analysis..."),
    ("suggestions", "Generating improvement suggestions..."),
    ("plugins", "Running plugin analyzers..."),
    ("aggregating", "Aggregating scores and grading..."),
]


class AnalysisOrchestrator:
    """Coordinate the full analysis pipeline from image path to completed report."""

    def __init__(
        self,
        settings: Settings | None = None,
        skip_ai: bool = False,
        skip_suggestions: bool = False,
    ) -> None:
        self._settings = settings or Settings()
        self._skip_ai = skip_ai
        self._skip_suggestions = skip_suggestions
        self.warnings: list[str] = []
        self._plugin_registry = self._load_plugins()

    def _load_plugins(self):  # noqa: ANN202
        from visionscore.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.discover_entry_points()
        plugin_dir = self._settings.plugin_dir
        if plugin_dir and plugin_dir.is_dir():
            registry.discover_directory(plugin_dir)
        if self._settings.enable_bundled_plugins:
            from visionscore.plugins import register_bundled_plugins

            register_bundled_plugins(registry)
        return registry

    def run(
        self,
        image_path: Path,
        progress_callback: Callable[[str, int, int, str], None] | None = None,
    ) -> AnalysisReport:
        self.warnings = []
        start = time.perf_counter()
        total = len(_STAGES)

        def _notify(stage_index: int) -> None:
            if progress_callback:
                name, msg = _STAGES[stage_index]
                progress_callback(name, stage_index + 1, total, msg)

        _notify(0)
        image = load_image(image_path, max_size=self._settings.max_image_size)
        _notify(1)
        meta = extract_metadata(image_path)

        # Technical analysis (always runs)
        _notify(2)
        from visionscore.analyzers.technical import TechnicalAnalyzer

        tech_analyzer = TechnicalAnalyzer(thresholds=self._settings.thresholds)
        technical = tech_analyzer.analyze(image, metadata=meta)

        # Aesthetic analysis (optional - needs NIMA weights)
        _notify(3)
        aesthetic = None
        try:
            from visionscore.analyzers.aesthetic import AestheticAnalyzer

            if self._settings.custom_model_path and self._settings.custom_model_path.is_file():
                model_path = self._settings.custom_model_path
            else:
                finetuned = self._settings.model_dir / "nima_finetuned.pth"
                base = self._settings.model_dir / "nima_mobilenetv2.pth"
                model_path = finetuned if finetuned.is_file() else base
            aes_analyzer = AestheticAnalyzer(model_path=model_path, device=self._settings.device)
            aesthetic = aes_analyzer.analyze(image, metadata=meta)
        except FileNotFoundError:
            self.warnings.append(
                "Aesthetic scoring skipped: NIMA weights not found. "
                "Run: python scripts/download_models.py"
            )
        except Exception as e:
            self.warnings.append(f"Aesthetic scoring error: {e}")

        # Composition analysis (always runs)
        _notify(4)
        from visionscore.analyzers.composition import CompositionAnalyzer

        comp_analyzer = CompositionAnalyzer()
        composition = comp_analyzer.analyze(image, metadata=meta)

        # AI feedback (optional - needs Ollama)
        _notify(5)
        ai_feedback = None
        if not self._skip_ai:
            try:
                from visionscore.analyzers.ai_feedback import AIFeedbackAnalyzer

                ai_analyzer = AIFeedbackAnalyzer(
                    host=self._settings.ollama_host,
                    model=self._settings.ollama_model,
                )
                ai_feedback = ai_analyzer.analyze(image, metadata=meta)
            except ConnectionError:
                self.warnings.append(
                    "AI feedback skipped: Ollama not available. "
                    "Run: ollama serve && ollama pull llava"
                )
            except Exception as e:
                self.warnings.append(f"AI feedback error: {e}")
        else:
            self.warnings.append("AI feedback skipped: --skip-ai flag set.")

        # Improvement suggestions (optional)
        _notify(6)
        suggestions = None
        if not self._skip_suggestions:
            try:
                from visionscore.analyzers.suggestions import SuggestionsAnalyzer

                suggestions_analyzer = SuggestionsAnalyzer(
                    technical=technical,
                    composition=composition,
                    ai_feedback=ai_feedback,
                    output_dir=image_path.parent,
                    ollama_host=self._settings.ollama_host if not self._skip_ai else None,
                    ollama_model=self._settings.ollama_model,
                    thresholds=self._settings.suggestion_thresholds,
                )
                suggestions = suggestions_analyzer.analyze(image, metadata=meta)
            except Exception as e:
                self.warnings.append(f"Suggestions error: {e}")

        # Plugin analyzers
        _notify(7)
        plugin_results: dict[str, object] = {}
        plugin_weights: dict[str, tuple[float, str]] = {}
        for info, analyzer_cls in self._plugin_registry.get_all():
            try:
                analyzer = analyzer_cls()
                result = analyzer.analyze(image, metadata=meta)
                plugin_results[info.name] = result.model_dump()
                if info.score_weight > 0:
                    plugin_weights[info.name] = (info.score_weight, info.score_field)
            except Exception as e:
                self.warnings.append(f"Plugin '{info.display_name}' error: {e}")

        # Build report, aggregate and grade
        _notify(8)
        report = AnalysisReport(
            image_meta=meta,
            technical=technical,
            aesthetic=aesthetic,
            composition=composition,
            ai_feedback=ai_feedback,
            suggestions=suggestions,
            plugin_results=plugin_results,
        )

        aggregator = ScoreAggregator(weights=self._settings.analysis_weights)
        report.overall_score = aggregator.aggregate(report, plugin_weights=plugin_weights)
        report.grade = assign_grade(report.overall_score)
        report.analysis_time_seconds = round(time.perf_counter() - start, 3)

        return report

    def run_batch(
        self,
        directory: Path,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> BatchResult:
        """Analyze all supported images in a directory."""
        self.warnings = []
        start = time.perf_counter()

        image_files = sorted(
            f for f in directory.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        results: list[BatchImageResult] = []
        scores: list[float] = []
        grade_counts: dict[str, int] = {}
        batch_warnings: list[str] = []
        best_image, best_score = "", 0.0
        worst_image, worst_score = "", 100.0

        for i, path in enumerate(image_files):
            try:
                report = self.run(path)
                # Capture per-image warnings before next run() resets them
                batch_warnings.extend(self.warnings)
                results.append(BatchImageResult(report=report, filename=path.name))
                scores.append(report.overall_score)

                grade_name = report.grade.value
                grade_counts[grade_name] = grade_counts.get(grade_name, 0) + 1

                if report.overall_score >= best_score:
                    best_score = report.overall_score
                    best_image = path.name
                if report.overall_score < worst_score:
                    worst_score = report.overall_score
                    worst_image = path.name
            except Exception as e:
                results.append(BatchImageResult(error=str(e), filename=path.name))
                batch_warnings.append(f"{path.name}: {e}")

            if progress_callback:
                progress_callback(path.name, i + 1, len(image_files))

        successful = len(scores)
        failed = len(results) - successful
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0

        self.warnings = batch_warnings

        batch = BatchResult(
            directory=str(directory),
            total_images=len(image_files),
            successful=successful,
            failed=failed,
            results=results,
            average_score=avg,
            best_image=best_image,
            best_score=best_score,
            worst_image=worst_image,
            worst_score=worst_score,
            grade_distribution=grade_counts,
            total_time_seconds=round(time.perf_counter() - start, 3),
        )

        return batch
