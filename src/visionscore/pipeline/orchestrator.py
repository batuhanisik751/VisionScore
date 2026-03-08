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


class AnalysisOrchestrator:
    """Coordinate the full analysis pipeline from image path to completed report."""

    def __init__(self, settings: Settings | None = None, skip_ai: bool = False) -> None:
        self._settings = settings or Settings()
        self._skip_ai = skip_ai
        self.warnings: list[str] = []

    def run(self, image_path: Path) -> AnalysisReport:
        self.warnings = []
        start = time.perf_counter()

        image = load_image(image_path, max_size=self._settings.max_image_size)
        meta = extract_metadata(image_path)

        # Technical analysis (always runs)
        from visionscore.analyzers.technical import TechnicalAnalyzer

        tech_analyzer = TechnicalAnalyzer(thresholds=self._settings.thresholds)
        technical = tech_analyzer.analyze(image, metadata=meta)

        # Aesthetic analysis (optional - needs NIMA weights)
        aesthetic = None
        try:
            from visionscore.analyzers.aesthetic import AestheticAnalyzer

            model_path = self._settings.model_dir / "nima_mobilenetv2.pth"
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
        from visionscore.analyzers.composition import CompositionAnalyzer

        comp_analyzer = CompositionAnalyzer()
        composition = comp_analyzer.analyze(image, metadata=meta)

        # AI feedback (optional - needs Ollama)
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

        # Build report
        report = AnalysisReport(
            image_meta=meta,
            technical=technical,
            aesthetic=aesthetic,
            composition=composition,
            ai_feedback=ai_feedback,
        )

        # Aggregate and grade
        aggregator = ScoreAggregator(weights=self._settings.analysis_weights)
        report.overall_score = aggregator.aggregate(report)
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
