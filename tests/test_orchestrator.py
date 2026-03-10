from __future__ import annotations

from visionscore.models import AnalysisReport, Grade
from visionscore.pipeline.orchestrator import AnalysisOrchestrator


class TestOrchestrator:
    def test_returns_analysis_report(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert isinstance(report, AnalysisReport)

    def test_has_technical_and_composition(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert report.technical is not None
        assert report.composition is not None

    def test_skip_ai_sets_none(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert report.ai_feedback is None
        assert any("--skip-ai" in w for w in orch.warnings)

    def test_overall_score_populated(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert report.overall_score > 0

    def test_grade_assigned(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert report.grade in list(Grade)

    def test_analysis_time_recorded(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path)
        assert report.analysis_time_seconds > 0

    def test_progress_callback_called_for_all_stages(self, normal_image_path) -> None:
        from unittest.mock import MagicMock

        cb = MagicMock()
        orch = AnalysisOrchestrator(skip_ai=True)
        orch.run(normal_image_path, progress_callback=cb)
        assert cb.call_count == 9
        # Verify stages arrive in order with correct indices
        for i, call in enumerate(cb.call_args_list):
            stage_name, stage_index, total, message = call.args
            assert stage_index == i + 1
            assert total == 9
            assert isinstance(stage_name, str)
            assert isinstance(message, str)

    def test_no_callback_still_works(self, normal_image_path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        report = orch.run(normal_image_path, progress_callback=None)
        assert isinstance(report, AnalysisReport)

    def test_parallel_stages_all_complete(self, normal_image_path) -> None:
        """All analyzer stages report completion regardless of execution order."""
        from unittest.mock import MagicMock

        cb = MagicMock()
        orch = AnalysisOrchestrator(skip_ai=True)
        orch.run(normal_image_path, progress_callback=cb)

        reported_stages = {call.args[0] for call in cb.call_args_list}
        expected = {
            "loading", "metadata", "technical", "aesthetic",
            "composition", "ai_feedback", "suggestions",
            "plugins", "aggregating",
        }
        assert reported_stages == expected
