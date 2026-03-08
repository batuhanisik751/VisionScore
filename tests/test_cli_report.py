from __future__ import annotations

import io

from rich.console import Console

from visionscore.models import (
    AestheticScore,
    AIFeedback,
    AnalysisReport,
    CompositionScore,
    Grade,
    ImageMeta,
    TechnicalScore,
)
from visionscore.output.cli_report import _diff_str, render_comparison
from visionscore.output.comparison import build_comparison


def _make_report(
    overall: float = 70.0,
    grade: Grade = Grade.B,
    tech_overall: float = 70.0,
    aes_overall: float = 70.0,
    comp_overall: float = 70.0,
    ai_score: float = 70.0,
    path: str = "img.jpg",
) -> AnalysisReport:
    return AnalysisReport(
        image_meta=ImageMeta(path=path, width=200, height=200, format="JPEG"),
        technical=TechnicalScore(
            sharpness=70, exposure=70, noise=70, dynamic_range=70, overall=tech_overall
        ),
        aesthetic=AestheticScore(nima_score=70, std_dev=1.0, confidence=0.9, overall=aes_overall),
        composition=CompositionScore(
            rule_of_thirds=70, subject_position=70, horizon=70, balance=70, overall=comp_overall
        ),
        ai_feedback=AIFeedback(
            description="Test",
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


class TestDiffStr:
    def test_positive_diff_shows_green_arrow_up(self) -> None:
        result = _diff_str(5.0)
        assert "green" in result
        assert "+" in result

    def test_negative_diff_shows_red_arrow_down(self) -> None:
        result = _diff_str(-5.0)
        assert "red" in result

    def test_near_zero_shows_dim(self) -> None:
        result = _diff_str(0.0)
        assert "dim" in result
        assert "0.0" in result

    def test_exactly_at_threshold(self) -> None:
        # _diff_str uses abs(diff) < 0.5 for dim; 0.5 is NOT < 0.5, so it shows color
        result_below = _diff_str(0.4)
        assert "dim" in result_below
        result_at = _diff_str(0.5)
        assert "green" in result_at

    def test_negative_threshold(self) -> None:
        result = _diff_str(-0.5)
        assert "red" in result

    def test_large_positive(self) -> None:
        result = _diff_str(25.3)
        assert "+25.3" in result

    def test_large_negative(self) -> None:
        result = _diff_str(-15.7)
        assert "-15.7" in result


def _capture_console() -> tuple[Console, io.StringIO]:
    buf = io.StringIO()
    c = Console(file=buf, force_terminal=True, width=120)
    return c, buf


class TestRenderComparison:
    def test_renders_without_error(self) -> None:
        a = _make_report(overall=60.0, path="a.jpg")
        b = _make_report(overall=80.0, path="b.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "Comparison" in output

    def test_shows_image_paths(self) -> None:
        a = _make_report(path="photo_before.jpg")
        b = _make_report(path="photo_after.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "photo_before.jpg" in output
        assert "photo_after.jpg" in output

    def test_shows_improved_list(self) -> None:
        a = _make_report(overall=50.0, tech_overall=50.0, path="a.jpg")
        b = _make_report(overall=70.0, tech_overall=70.0, path="b.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "Improved" in output

    def test_shows_degraded_list(self) -> None:
        a = _make_report(overall=80.0, tech_overall=80.0, path="a.jpg")
        b = _make_report(overall=50.0, tech_overall=50.0, path="b.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "Degraded" in output

    def test_no_changes_message(self) -> None:
        a = _make_report(overall=70.0, path="a.jpg")
        b = _make_report(overall=70.0, path="b.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "No significant changes" in output

    def test_renders_with_warnings(self) -> None:
        a = _make_report(path="a.jpg")
        b = _make_report(path="b.jpg")
        comp = build_comparison(a, b)
        c, buf = _capture_console()
        render_comparison(comp, c, warnings=["Test warning msg"])
        output = buf.getvalue()
        assert "Test warning msg" in output

    def test_minimal_reports(self) -> None:
        """Reports without aesthetic/composition/ai should not crash."""
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
        c, buf = _capture_console()
        render_comparison(comp, c)
        output = buf.getvalue()
        assert "Comparison" in output
