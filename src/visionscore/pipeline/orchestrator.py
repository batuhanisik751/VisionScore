from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
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

        counter = 0
        counter_lock = threading.Lock()

        def _notify(stage_name: str, message: str) -> None:
            nonlocal counter
            with counter_lock:
                counter += 1
                idx = counter
            if progress_callback:
                progress_callback(stage_name, idx, total, message)

        # Phase 1: Sequential setup ------------------------------------------
        _notify("loading", "Loading image...")
        image = load_image(image_path, max_size=self._settings.max_image_size)
        _notify("metadata", "Extracting metadata...")
        meta = extract_metadata(image_path)

        # Phase 2: Parallel analyzers -----------------------------------------
        # These 5 tasks are independent — they all need only (image, metadata).

        def _run_technical():  # noqa: ANN202
            from visionscore.analyzers.technical import TechnicalAnalyzer

            analyzer = TechnicalAnalyzer(thresholds=self._settings.thresholds)
            return analyzer.analyze(image, metadata=meta)

        def _run_aesthetic():  # noqa: ANN202
            try:
                from visionscore.analyzers.aesthetic import AestheticAnalyzer

                if self._settings.custom_model_path and self._settings.custom_model_path.is_file():
                    model_path = self._settings.custom_model_path
                else:
                    finetuned = self._settings.model_dir / "nima_finetuned.pth"
                    base = self._settings.model_dir / "nima_mobilenetv2.pth"
                    model_path = finetuned if finetuned.is_file() else base
                aes_analyzer = AestheticAnalyzer(
                    model_path=model_path, device=self._settings.device
                )
                return aes_analyzer.analyze(image, metadata=meta)
            except FileNotFoundError:
                self.warnings.append(
                    "Aesthetic scoring skipped: NIMA weights not found. "
                    "Run: python scripts/download_models.py"
                )
                return None
            except Exception as e:
                self.warnings.append(f"Aesthetic scoring error: {e}")
                return None

        def _run_composition():  # noqa: ANN202
            from visionscore.analyzers.composition import CompositionAnalyzer

            comp_analyzer = CompositionAnalyzer()
            return comp_analyzer.analyze(image, metadata=meta)

        def _run_ai_feedback():  # noqa: ANN202
            if self._skip_ai:
                self.warnings.append("AI feedback skipped: --skip-ai flag set.")
                return None
            try:
                from visionscore.analyzers.ai_feedback import AIFeedbackAnalyzer

                ai_analyzer = AIFeedbackAnalyzer(
                    host=self._settings.ollama_host,
                    model=self._settings.ollama_model,
                )
                return ai_analyzer.analyze(image, metadata=meta)
            except ConnectionError:
                self.warnings.append(
                    "AI feedback skipped: Ollama not available. "
                    "Run: ollama serve && ollama pull llava"
                )
                return None
            except Exception as e:
                self.warnings.append(f"AI feedback error: {e}")
                return None

        def _run_plugins() -> tuple[dict[str, object], dict[str, tuple[float, str]]]:
            results: dict[str, object] = {}
            weights: dict[str, tuple[float, str]] = {}
            for info, analyzer_cls in self._plugin_registry.get_all():
                try:
                    analyzer = analyzer_cls()
                    result = analyzer.analyze(image, metadata=meta)
                    results[info.name] = result.model_dump()
                    if info.score_weight > 0:
                        weights[info.name] = (info.score_weight, info.score_field)
                except Exception as e:
                    self.warnings.append(f"Plugin '{info.display_name}' error: {e}")
            return results, weights

        _STAGE_MESSAGES = {
            "technical": "Running technical analysis...",
            "aesthetic": "Running aesthetic analysis...",
            "composition": "Running composition analysis...",
            "ai_feedback": "Running AI feedback analysis...",
            "plugins": "Running plugin analyzers...",
        }

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(_run_technical): "technical",
                pool.submit(_run_aesthetic): "aesthetic",
                pool.submit(_run_composition): "composition",
                pool.submit(_run_ai_feedback): "ai_feedback",
                pool.submit(_run_plugins): "plugins",
            }
            completed_results: dict[str, object] = {}
            for future in as_completed(futures):
                stage_name = futures[future]
                completed_results[stage_name] = future.result()
                _notify(stage_name, _STAGE_MESSAGES[stage_name])

        technical = completed_results["technical"]
        aesthetic = completed_results["aesthetic"]
        composition = completed_results["composition"]
        ai_feedback = completed_results["ai_feedback"]
        plugin_results, plugin_weights = completed_results["plugins"]

        # Phase 3: Suggestions (depends on technical + composition + ai_feedback)
        _notify("suggestions", "Generating improvement suggestions...")
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

        # Phase 4: Aggregation ------------------------------------------------
        _notify("aggregating", "Aggregating scores and grading...")
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
