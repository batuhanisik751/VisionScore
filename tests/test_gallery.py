"""Tests for the HTML gallery generator."""

from __future__ import annotations

import pytest

from visionscore.models import (
    AnalysisReport,
    BatchImageResult,
    BatchResult,
    Grade,
    ImageMeta,
)
from visionscore.output.html_gallery import format_html_gallery


def _make_batch(*scores: tuple[str, float, str]) -> BatchResult:
    """Build a minimal BatchResult from (filename, score, grade) tuples."""
    results = []
    for filename, score, grade in scores:
        report = AnalysisReport(
            image_meta=ImageMeta(path=filename),
            overall_score=score,
            grade=Grade(grade),
        )
        results.append(BatchImageResult(report=report, filename=filename))

    successful = len(results)
    best = max(scores, key=lambda t: t[1])
    worst = min(scores, key=lambda t: t[1])
    avg = sum(s for _, s, _ in scores) / len(scores) if scores else 0
    dist: dict[str, int] = {}
    for _, _, g in scores:
        dist[g] = dist.get(g, 0) + 1

    return BatchResult(
        directory="/test",
        total_images=successful,
        successful=successful,
        failed=0,
        results=results,
        average_score=avg,
        best_image=best[0],
        best_score=best[1],
        worst_image=worst[0],
        worst_score=worst[1],
        grade_distribution=dist,
    )


class TestFormatHtmlGallery:
    def test_returns_valid_html(self):
        batch = _make_batch(("a.jpg", 85.0, "A"), ("b.jpg", 60.0, "C"))
        html = format_html_gallery(batch)
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_contains_all_images(self):
        batch = _make_batch(
            ("alpha.jpg", 90.0, "A"),
            ("beta.jpg", 70.0, "B"),
            ("gamma.jpg", 50.0, "D"),
        )
        html = format_html_gallery(batch)
        assert "alpha.jpg" in html
        assert "beta.jpg" in html
        assert "gamma.jpg" in html

    def test_sorted_by_score(self):
        batch = _make_batch(
            ("low.jpg", 40.0, "D"),
            ("high.jpg", 95.0, "S"),
            ("mid.jpg", 70.0, "B"),
        )
        html = format_html_gallery(batch)
        # #1 rank should appear with the highest scorer
        pos_high = html.index("high.jpg")
        pos_mid = html.index("mid.jpg")
        pos_low = html.index("low.jpg")
        assert pos_high < pos_mid < pos_low

    def test_potd_section(self):
        batch = _make_batch(("winner.jpg", 98.0, "S"), ("other.jpg", 50.0, "D"))
        html = format_html_gallery(batch)
        assert "Photo of the Day" in html
        assert "winner.jpg" in html

    def test_stats_section(self):
        batch = _make_batch(("a.jpg", 80.0, "B"), ("b.jpg", 60.0, "C"))
        html = format_html_gallery(batch)
        assert "70.0" in html  # average
        assert str(batch.successful) in html

    def test_empty_batch(self):
        batch = BatchResult(directory="/empty", total_images=0, successful=0, failed=0)
        html = format_html_gallery(batch)
        assert "<html" in html
        assert "No images" in html

    def test_custom_title(self):
        batch = _make_batch(("a.jpg", 80.0, "B"))
        html = format_html_gallery(batch, title="My Custom Gallery")
        assert "<title>My Custom Gallery</title>" in html
        assert "My Custom Gallery" in html
