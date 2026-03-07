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
