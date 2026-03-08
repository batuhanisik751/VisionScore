from __future__ import annotations

import json

from visionscore.models import (
    AestheticScore,
    AIFeedback,
    AnalysisReport,
    CompositionScore,
    Grade,
    ImageMeta,
    TechnicalScore,
)
from visionscore.output.comparison import _diff, build_comparison, format_comparison_json


def _make_report(
    overall: float = 70.0,
    grade: Grade = Grade.B,
    tech_overall: float = 70.0,
    aes_overall: float = 70.0,
    comp_overall: float = 70.0,
    ai_score: float = 70.0,
    path: str = "img.jpg",
    sharpness: float = 70.0,
    exposure: float = 70.0,
    noise: float = 70.0,
    dynamic_range: float = 70.0,
    nima_score: float = 70.0,
    rot: float = 70.0,
    subject_position: float = 70.0,
    horizon: float = 70.0,
    balance: float = 70.0,
) -> AnalysisReport:
    return AnalysisReport(
        image_meta=ImageMeta(path=path, width=200, height=200, format="JPEG"),
        technical=TechnicalScore(
            sharpness=sharpness,
            exposure=exposure,
            noise=noise,
            dynamic_range=dynamic_range,
            overall=tech_overall,
        ),
        aesthetic=AestheticScore(nima_score=nima_score, std_dev=1.0, confidence=0.9, overall=aes_overall),
        composition=CompositionScore(
            rule_of_thirds=rot,
            subject_position=subject_position,
            horizon=horizon,
            balance=balance,
            overall=comp_overall,
        ),
        ai_feedback=AIFeedback(
            description="Test image",
            genre="test",
            strengths=["sharp"],
            improvements=["color"],
            mood="neutral",
            score=ai_score,
            reasoning="ok",
        ),
        overall_score=overall,
        grade=grade,
    )


class TestDiff:
    def test_positive_diff(self) -> None:
        sd = _diff("Metric", 50.0, 80.0)
        assert sd.label == "Metric"
        assert sd.score_a == 50.0
        assert sd.score_b == 80.0
        assert sd.diff == 30.0

    def test_negative_diff(self) -> None:
        sd = _diff("Metric", 80.0, 50.0)
        assert sd.diff == -30.0

    def test_zero_diff(self) -> None:
        sd = _diff("Metric", 60.0, 60.0)
        assert sd.diff == 0.0

    def test_rounds_values(self) -> None:
        sd = _diff("Metric", 33.333, 66.666)
        assert sd.score_a == 33.3
        assert sd.score_b == 66.7
        assert sd.diff == 33.3


class TestBuildComparison:
    def test_identical_reports_no_diffs(self) -> None:
        a = _make_report(overall=70.0, path="a.jpg")
        b = _make_report(overall=70.0, path="b.jpg")
        comp = build_comparison(a, b)
        assert comp.overall_diff == 0.0
        assert comp.improved == []
        assert comp.degraded == []

    def test_improved_overall(self) -> None:
        a = _make_report(overall=60.0, path="a.jpg")
        b = _make_report(overall=80.0, path="b.jpg")
        comp = build_comparison(a, b)
        assert comp.overall_diff == 20.0
        assert "Overall" in comp.improved
        assert comp.degraded == []

    def test_degraded_overall(self) -> None:
        a = _make_report(overall=80.0, path="a.jpg")
        b = _make_report(overall=60.0, path="b.jpg")
        comp = build_comparison(a, b)
        assert comp.overall_diff == -20.0
        assert "Overall" in comp.degraded

    def test_category_diffs_populated(self) -> None:
        a = _make_report(tech_overall=60.0, aes_overall=70.0, comp_overall=50.0, ai_score=40.0)
        b = _make_report(tech_overall=80.0, aes_overall=70.0, comp_overall=60.0, ai_score=30.0)
        comp = build_comparison(a, b)
        labels = [d.label for d in comp.category_diffs]
        assert "Technical" in labels
        assert "Aesthetic" in labels
        assert "Composition" in labels
        assert "AI Feedback" in labels

    def test_detail_diffs_populated(self) -> None:
        a = _make_report(sharpness=50.0, exposure=60.0, noise=70.0, dynamic_range=80.0)
        b = _make_report(sharpness=80.0, exposure=60.0, noise=50.0, dynamic_range=90.0)
        comp = build_comparison(a, b)
        labels = [d.label for d in comp.detail_diffs]
        assert "Sharpness" in labels
        assert "Exposure" in labels
        assert "Noise" in labels
        assert "Dynamic Range" in labels
        assert "NIMA Score" in labels
        assert "Rule of Thirds" in labels

    def test_threshold_boundary(self) -> None:
        """Diffs exactly at threshold (1.0) should count as improved/degraded."""
        a = _make_report(overall=70.0, tech_overall=50.0)
        b = _make_report(overall=71.0, tech_overall=51.0)
        comp = build_comparison(a, b)
        assert "Overall" in comp.improved
        assert "Technical" in comp.improved

    def test_below_threshold_not_flagged(self) -> None:
        """Diffs below 1.0 threshold should not appear in improved/degraded."""
        a = _make_report(overall=70.0, tech_overall=50.0)
        b = _make_report(overall=70.5, tech_overall=50.5)
        comp = build_comparison(a, b)
        assert "Overall" not in comp.improved
        assert "Technical" not in comp.improved

    def test_missing_categories_skipped(self) -> None:
        """Reports without aesthetic/composition/ai should produce fewer diffs."""
        a = AnalysisReport(
            image_meta=ImageMeta(path="a.jpg", width=200, height=200, format="JPEG"),
            technical=TechnicalScore(sharpness=70, exposure=70, noise=70, dynamic_range=70, overall=70),
            overall_score=70.0,
            grade=Grade.B,
        )
        b = AnalysisReport(
            image_meta=ImageMeta(path="b.jpg", width=200, height=200, format="JPEG"),
            technical=TechnicalScore(sharpness=80, exposure=80, noise=80, dynamic_range=80, overall=80),
            overall_score=80.0,
            grade=Grade.B,
        )
        comp = build_comparison(a, b)
        cat_labels = [d.label for d in comp.category_diffs]
        assert "Technical" in cat_labels
        assert "Aesthetic" not in cat_labels
        assert "Composition" not in cat_labels
        assert "AI Feedback" not in cat_labels

    def test_reports_stored(self) -> None:
        a = _make_report(path="a.jpg")
        b = _make_report(path="b.jpg")
        comp = build_comparison(a, b)
        assert comp.report_a.image_meta.path == "a.jpg"
        assert comp.report_b.image_meta.path == "b.jpg"


class TestFormatComparisonJson:
    def test_returns_valid_json(self) -> None:
        a = _make_report(overall=60.0, path="a.jpg")
        b = _make_report(overall=80.0, path="b.jpg")
        comp = build_comparison(a, b)
        result = format_comparison_json(comp)
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_overall_diff(self) -> None:
        a = _make_report(overall=60.0, path="a.jpg")
        b = _make_report(overall=80.0, path="b.jpg")
        comp = build_comparison(a, b)
        result = format_comparison_json(comp)
        data = json.loads(result)
        assert data["overall_diff"] == 20.0

    def test_contains_improved_degraded(self) -> None:
        a = _make_report(overall=60.0, tech_overall=80.0, path="a.jpg")
        b = _make_report(overall=80.0, tech_overall=60.0, path="b.jpg")
        comp = build_comparison(a, b)
        result = format_comparison_json(comp)
        data = json.loads(result)
        assert "improved" in data
        assert "degraded" in data
        assert "Overall" in data["improved"]
        assert "Technical" in data["degraded"]

    def test_pretty_printed(self) -> None:
        a = _make_report(path="a.jpg")
        b = _make_report(path="b.jpg")
        comp = build_comparison(a, b)
        result = format_comparison_json(comp)
        assert "\n" in result  # pretty printed has newlines
