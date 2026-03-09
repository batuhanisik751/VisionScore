from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from visionscore.cli import app
from visionscore.models import (
    AestheticScore,
    AIFeedback,
    AnalysisReport,
    BatchImageResult,
    BatchResult,
    CompositionScore,
    Grade,
    ImageMeta,
    TechnicalScore,
)

runner = CliRunner()


def _fake_report(path: str = "img.jpg", overall: float = 70.0) -> AnalysisReport:
    return AnalysisReport(
        image_meta=ImageMeta(path=path, width=200, height=200, format="JPEG"),
        technical=TechnicalScore(sharpness=70, exposure=70, noise=70, dynamic_range=70, overall=70),
        aesthetic=AestheticScore(nima_score=70, std_dev=1.0, confidence=0.9, overall=70),
        composition=CompositionScore(
            rule_of_thirds=70, subject_position=70, horizon=70, balance=70, overall=70
        ),
        ai_feedback=AIFeedback(
            description="Test",
            genre="test",
            strengths=["sharp"],
            improvements=["color"],
            mood="neutral",
            score=70,
            reasoning="ok",
        ),
        overall_score=overall,
        grade=Grade.B,
    )


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_info_command(normal_image_path: Path):
    result = runner.invoke(app, ["info", str(normal_image_path)])
    assert result.exit_code == 0
    assert "200" in result.output


def test_analyze_command_shows_scores(normal_image_path: Path):
    result = runner.invoke(app, ["analyze", str(normal_image_path)])
    assert result.exit_code == 0
    assert "Technical Quality" in result.output


class TestCompareCommand:
    def test_compare_text_output(self, sharp_image_path: Path, blurry_image_path: Path) -> None:
        mock_orch = MagicMock()
        mock_orch.run.side_effect = [
            _fake_report(str(sharp_image_path), overall=80.0),
            _fake_report(str(blurry_image_path), overall=60.0),
        ]
        mock_orch.warnings = []

        with patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator", return_value=mock_orch):
            result = runner.invoke(
                app, ["compare", str(sharp_image_path), str(blurry_image_path)]
            )
        assert result.exit_code == 0
        assert "Comparison" in result.output

    def test_compare_json_output(self, sharp_image_path: Path, blurry_image_path: Path) -> None:
        mock_orch = MagicMock()
        mock_orch.run.side_effect = [
            _fake_report(str(sharp_image_path), overall=80.0),
            _fake_report(str(blurry_image_path), overall=60.0),
        ]
        mock_orch.warnings = []

        with patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator", return_value=mock_orch):
            result = runner.invoke(
                app,
                ["compare", str(sharp_image_path), str(blurry_image_path), "--output", "json"],
            )
        assert result.exit_code == 0
        assert "overall_diff" in result.output

    def test_compare_invalid_file(self, tmp_path: Path) -> None:
        fake_a = tmp_path / "nonexistent_a.jpg"
        fake_b = tmp_path / "nonexistent_b.jpg"
        result = runner.invoke(app, ["compare", str(fake_a), str(fake_b)])
        assert result.exit_code != 0

    def test_compare_save_output(
        self, sharp_image_path: Path, blurry_image_path: Path, tmp_path: Path
    ) -> None:
        out_file = tmp_path / "comparison.json"
        mock_orch = MagicMock()
        mock_orch.run.side_effect = [
            _fake_report(str(sharp_image_path), overall=80.0),
            _fake_report(str(blurry_image_path), overall=60.0),
        ]
        mock_orch.warnings = []

        with patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator", return_value=mock_orch):
            result = runner.invoke(
                app,
                [
                    "compare",
                    str(sharp_image_path),
                    str(blurry_image_path),
                    "--save",
                    str(out_file),
                ],
            )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "overall_diff" in content


class TestGalleryCommand:
    def _fake_batch(self) -> BatchResult:
        rpt = _fake_report("photo.jpg", overall=85.0)
        return BatchResult(
            directory="/photos",
            total_images=1,
            successful=1,
            failed=0,
            results=[BatchImageResult(report=rpt, filename="photo.jpg")],
            average_score=85.0,
            best_image="photo.jpg",
            best_score=85.0,
            worst_image="photo.jpg",
            worst_score=85.0,
            grade_distribution={"A": 1},
        )

    def test_gallery_creates_file(self, tmp_path: Path) -> None:
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        out_file = tmp_path / "gallery.html"

        mock_orch = MagicMock()
        mock_orch.run_batch.return_value = self._fake_batch()
        mock_orch.warnings = []

        with patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator", return_value=mock_orch):
            result = runner.invoke(
                app, ["gallery", str(img_dir), "--output", str(out_file)]
            )
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "<html" in content
        assert "photo.jpg" in content

    def test_gallery_custom_title(self, tmp_path: Path) -> None:
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        out_file = tmp_path / "gallery.html"

        mock_orch = MagicMock()
        mock_orch.run_batch.return_value = self._fake_batch()
        mock_orch.warnings = []

        with patch("visionscore.pipeline.orchestrator.AnalysisOrchestrator", return_value=mock_orch):
            result = runner.invoke(
                app, ["gallery", str(img_dir), "--output", str(out_file), "--title", "My Photos"]
            )
        assert result.exit_code == 0
        content = out_file.read_text()
        assert "My Photos" in content

    def test_gallery_invalid_directory(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "nonexistent"
        result = runner.invoke(app, ["gallery", str(fake_dir)])
        assert result.exit_code == 1


class TestTrainCommand:
    def test_train_missing_dir(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "nonexistent"
        csv_path = tmp_path / "ratings.csv"
        csv_path.write_text("img.jpg,5\n")
        result = runner.invoke(app, ["train", str(fake_dir), str(csv_path)])
        assert result.exit_code == 1

    def test_train_missing_csv(self, tmp_path: Path) -> None:
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        fake_csv = tmp_path / "nonexistent.csv"
        result = runner.invoke(app, ["train", str(img_dir), str(fake_csv)])
        assert result.exit_code == 1

    def test_train_invalid_scale(self, tmp_path: Path) -> None:
        img_dir = tmp_path / "images"
        img_dir.mkdir()
        csv_path = tmp_path / "ratings.csv"
        csv_path.write_text("img.jpg,5\n")
        result = runner.invoke(
            app, ["train", str(img_dir), str(csv_path), "--scale", "invalid"]
        )
        assert result.exit_code == 1
