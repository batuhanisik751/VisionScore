from __future__ import annotations

import csv
import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from rich.console import Console
from typer.testing import CliRunner

from visionscore.cli import app
from visionscore.models import (
    AnalysisReport,
    BatchImageResult,
    BatchResult,
    Grade,
    ImageMeta,
    TechnicalScore,
)
from visionscore.output.cli_report import render_batch_report
from visionscore.output.csv_report import format_csv
from visionscore.pipeline.orchestrator import AnalysisOrchestrator

runner = CliRunner()


# --- Helpers ---


def _sample_batch_result(n: int = 3) -> BatchResult:
    """Build a BatchResult with n successful images for output tests."""
    results = []
    for i in range(n):
        score = 50.0 + i * 15
        report = AnalysisReport(
            image_meta=ImageMeta(path=f"img_{i}.jpg", width=200, height=200, format="JPEG"),
            technical=TechnicalScore(
                sharpness=score, exposure=score, noise=score, dynamic_range=score, overall=score
            ),
            overall_score=score,
            grade=Grade.C if score < 70 else Grade.B,
        )
        results.append(BatchImageResult(report=report, filename=f"img_{i}.jpg"))

    results.append(BatchImageResult(error="corrupt file", filename="bad.jpg"))

    return BatchResult(
        directory="/tmp/test",
        total_images=n + 1,
        successful=n,
        failed=1,
        results=results,
        average_score=round(sum(50.0 + i * 15 for i in range(n)) / n, 1),
        best_image=f"img_{n - 1}.jpg",
        best_score=50.0 + (n - 1) * 15,
        worst_image="img_0.jpg",
        worst_score=50.0,
        grade_distribution={"C": 2, "B": 1},
    )


# --- Orchestrator run_batch tests ---


class TestRunBatch:
    def test_returns_batch_result(self, image_dir: Path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(image_dir)
        assert isinstance(batch, BatchResult)

    def test_counts_images(self, image_dir: Path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(image_dir)
        assert batch.total_images > 0
        assert batch.successful == batch.total_images
        assert batch.failed == 0

    def test_best_worst_identified(self, image_dir: Path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(image_dir)
        assert batch.best_image != ""
        assert batch.worst_image != ""
        assert batch.best_score >= batch.worst_score

    def test_grade_distribution(self, image_dir: Path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(image_dir)
        assert len(batch.grade_distribution) > 0
        assert sum(batch.grade_distribution.values()) == batch.successful

    def test_empty_directory(self, tmp_path: Path) -> None:
        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(tmp_path)
        assert batch.total_images == 0
        assert batch.successful == 0
        assert batch.average_score == 0.0

    def test_skips_non_image_files(self, tmp_path: Path) -> None:
        (tmp_path / "notes.txt").write_text("not an image")
        (tmp_path / "data.csv").write_text("a,b,c")
        # Add one real image
        img = np.zeros((50, 50, 3), dtype=np.uint8)
        cv2.imwrite(str(tmp_path / "real.jpg"), img)

        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(tmp_path)
        assert batch.total_images == 1
        assert batch.results[0].filename == "real.jpg"

    def test_failed_image_tracked(self, tmp_path: Path) -> None:
        # Write invalid data with .jpg extension
        bad = tmp_path / "corrupt.jpg"
        bad.write_text("not image data")

        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(tmp_path)
        assert batch.total_images == 1
        assert batch.failed == 1
        assert batch.results[0].error is not None

    def test_progress_callback(self, image_dir: Path) -> None:
        calls: list[tuple[str, int, int]] = []

        def cb(filename: str, current: int, total: int) -> None:
            calls.append((filename, current, total))

        orch = AnalysisOrchestrator(skip_ai=True)
        batch = orch.run_batch(image_dir, progress_callback=cb)
        assert len(calls) == batch.total_images
        # Last call should have current == total
        assert calls[-1][1] == calls[-1][2]


# --- CSV format tests ---


class TestCsvFormat:
    def test_header_present(self) -> None:
        batch = _sample_batch_result()
        output = format_csv(batch)
        lines = output.strip().split("\n")
        assert "filename" in lines[0]
        assert "overall_score" in lines[0]
        assert "error" in lines[0]

    def test_one_row_per_image(self) -> None:
        batch = _sample_batch_result(3)
        output = format_csv(batch)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        # 1 header + 3 successful + 1 failed = 5
        assert len(rows) == 5

    def test_failed_image_error_column(self) -> None:
        batch = _sample_batch_result(1)
        output = format_csv(batch)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        error_idx = rows[0].index("error")
        # Last row is the failed image
        assert rows[-1][error_idx] == "corrupt file"

    def test_parseable_by_csv_reader(self) -> None:
        batch = _sample_batch_result()
        output = format_csv(batch)
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        assert all("filename" in r for r in rows)
        assert all("overall_score" in r for r in rows)


# --- CLI tests ---


class TestBatchCli:
    def test_command_runs(self, image_dir: Path) -> None:
        result = runner.invoke(app, ["analyze-batch", str(image_dir), "--skip-ai"])
        assert result.exit_code == 0
        assert "Batch Analysis Summary" in result.output

    def test_csv_output(self, image_dir: Path) -> None:
        result = runner.invoke(app, ["analyze-batch", str(image_dir), "--skip-ai", "--output", "csv"])
        assert result.exit_code == 0
        assert "filename" in result.output
        assert "overall_score" in result.output

    def test_empty_dir_message(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["analyze-batch", str(tmp_path), "--skip-ai"])
        assert result.exit_code == 0
        assert "No supported images" in result.output

    def test_nonexistent_dir_error(self) -> None:
        result = runner.invoke(app, ["analyze-batch", "/nonexistent/path"])
        assert result.exit_code == 1


# --- Render batch report tests ---


class TestRenderBatchReport:
    def test_does_not_raise(self) -> None:
        batch = _sample_batch_result()
        c = Console(file=io.StringIO())
        render_batch_report(batch, c)

    def test_shows_ranking(self) -> None:
        batch = _sample_batch_result()
        buf = io.StringIO()
        c = Console(file=buf, force_terminal=True)
        render_batch_report(batch, c)
        output = buf.getvalue()
        assert "Image Rankings" in output
        assert "img_0.jpg" in output
