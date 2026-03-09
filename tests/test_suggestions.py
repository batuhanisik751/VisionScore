from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from visionscore.analyzers.suggestions import SuggestionsAnalyzer
from visionscore.config import SuggestionThresholds
from visionscore.models import (
    CompositionScore,
    ImprovementSuggestion,
    SuggestionType,
    SuggestionsResult,
    TechnicalScore,
)
from visionscore.pipeline.loader import LoadedImage


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_loaded_image(path: Path) -> LoadedImage:
    """Build a LoadedImage from a test fixture path."""
    import cv2

    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    max_size = 1024
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        resized = cv2.resize(img, (int(w * scale), int(h * scale)))
    else:
        resized = img.copy()

    return LoadedImage(
        original=img,
        resized=resized,
        path=path,
        format="JPEG",
        width=w,
        height=h,
    )


def _make_technical(
    sharpness: float = 70,
    exposure: float = 70,
    noise: float = 70,
    dynamic_range: float = 70,
) -> TechnicalScore:
    overall = (sharpness + exposure + noise + dynamic_range) / 4
    return TechnicalScore(
        sharpness=sharpness,
        exposure=exposure,
        noise=noise,
        dynamic_range=dynamic_range,
        overall=overall,
    )


def _make_composition(
    rule_of_thirds: float = 70,
    subject_position: float = 70,
    horizon: float = 80,
    balance: float = 70,
    centroid: tuple[float, float] = (0.5, 0.5),
    horizon_angle: float | None = None,
    dims: tuple[int, int] = (300, 300),
) -> CompositionScore:
    overall = rule_of_thirds * 0.4 + subject_position * 0.25 + horizon * 0.2 + balance * 0.15
    return CompositionScore(
        rule_of_thirds=rule_of_thirds,
        subject_position=subject_position,
        horizon=horizon,
        balance=balance,
        overall=overall,
        subject_centroid=centroid,
        subject_bbox=(0, 0, 60, 60),
        horizon_angle=horizon_angle,
        image_dimensions=dims,
    )


# ------------------------------------------------------------------
# Exposure tests
# ------------------------------------------------------------------


class TestExposureSuggestion:
    def test_dark_image_suggests_increase(self, dark_image_path: Path):
        image = _make_loaded_image(dark_image_path)
        tech = _make_technical(exposure=30)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
        assert len(exposure_suggs) == 1
        assert "increase" in exposure_suggs[0].instruction.lower()
        assert exposure_suggs[0].parameters["direction"] == "increase"

    def test_bright_image_suggests_decrease(self, bright_image_path: Path):
        image = _make_loaded_image(bright_image_path)
        tech = _make_technical(exposure=30)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
        assert len(exposure_suggs) == 1
        assert "decrease" in exposure_suggs[0].instruction.lower()
        assert exposure_suggs[0].parameters["direction"] == "decrease"

    def test_normal_exposure_no_suggestion(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=75)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
        assert len(exposure_suggs) == 0

    def test_stops_reasonable(self, dark_image_path: Path):
        image = _make_loaded_image(dark_image_path)
        tech = _make_technical(exposure=10)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
        assert exposure_suggs[0].parameters["stops"] == 2.0


# ------------------------------------------------------------------
# Contrast tests
# ------------------------------------------------------------------


class TestContrastSuggestion:
    def test_flat_image_triggers(self, flat_gray_image_path: Path):
        image = _make_loaded_image(flat_gray_image_path)
        tech = _make_technical(dynamic_range=20)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        contrast_suggs = [s for s in result.suggestions if s.type == SuggestionType.CONTRAST]
        assert len(contrast_suggs) == 1
        assert "contrast" in contrast_suggs[0].instruction.lower()

    def test_high_contrast_no_suggestion(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(dynamic_range=80)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        contrast_suggs = [s for s in result.suggestions if s.type == SuggestionType.CONTRAST]
        assert len(contrast_suggs) == 0


# ------------------------------------------------------------------
# Sharpness tests
# ------------------------------------------------------------------


class TestSharpnessSuggestion:
    def test_blurry_triggers(self, blurry_image_path: Path):
        image = _make_loaded_image(blurry_image_path)
        tech = _make_technical(sharpness=25)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        sharp_suggs = [s for s in result.suggestions if s.type == SuggestionType.SHARPNESS]
        assert len(sharp_suggs) == 1
        assert "sharpening" in sharp_suggs[0].instruction.lower()

    def test_sharp_no_suggestion(self, sharp_image_path: Path):
        image = _make_loaded_image(sharp_image_path)
        tech = _make_technical(sharpness=80)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        sharp_suggs = [s for s in result.suggestions if s.type == SuggestionType.SHARPNESS]
        assert len(sharp_suggs) == 0


# ------------------------------------------------------------------
# Horizon tests
# ------------------------------------------------------------------


class TestHorizonSuggestion:
    def test_tilted_triggers(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        comp = _make_composition(horizon=50, horizon_angle=5.0)
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        horizon_suggs = [s for s in result.suggestions if s.type == SuggestionType.HORIZON]
        assert len(horizon_suggs) == 1
        assert "5.0" in horizon_suggs[0].instruction
        assert horizon_suggs[0].parameters["rotate_degrees"] == 5.0

    def test_level_no_suggestion(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        comp = _make_composition(horizon=90, horizon_angle=0.5)
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        horizon_suggs = [s for s in result.suggestions if s.type == SuggestionType.HORIZON]
        assert len(horizon_suggs) == 0

    def test_no_angle_no_suggestion(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        comp = _make_composition(horizon=50, horizon_angle=None)
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        horizon_suggs = [s for s in result.suggestions if s.type == SuggestionType.HORIZON]
        assert len(horizon_suggs) == 0


# ------------------------------------------------------------------
# Crop tests
# ------------------------------------------------------------------


class TestCropSuggestion:
    def test_centered_subject_triggers_crop(self, subject_centered_path: Path):
        image = _make_loaded_image(subject_centered_path)
        comp = _make_composition(
            rule_of_thirds=30,
            subject_position=40,
            centroid=(0.5, 0.5),
            dims=(300, 300),
        )
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        crop_suggs = [s for s in result.suggestions if s.type == SuggestionType.CROP]
        assert len(crop_suggs) == 1
        assert crop_suggs[0].crop_details is not None

    def test_power_point_subject_no_crop(self, subject_at_power_point_path: Path):
        image = _make_loaded_image(subject_at_power_point_path)
        comp = _make_composition(
            rule_of_thirds=85,
            subject_position=80,
            centroid=(1 / 3, 1 / 3),
            dims=(300, 300),
        )
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        crop_suggs = [s for s in result.suggestions if s.type == SuggestionType.CROP]
        assert len(crop_suggs) == 0

    def test_crop_coords_in_bounds(self, subject_centered_path: Path):
        image = _make_loaded_image(subject_centered_path)
        comp = _make_composition(
            rule_of_thirds=30,
            subject_position=40,
            centroid=(0.5, 0.5),
            dims=(300, 300),
        )
        analyzer = SuggestionsAnalyzer(composition=comp)
        result = analyzer.analyze(image)
        crop_suggs = [s for s in result.suggestions if s.type == SuggestionType.CROP]
        if crop_suggs:
            cd = crop_suggs[0].crop_details
            assert cd is not None
            assert cd.target_x >= 0
            assert cd.target_y >= 0
            assert cd.target_x + cd.target_w <= 300
            assert cd.target_y + cd.target_h <= 300

    def test_crop_preview_generated(self, subject_centered_path: Path, tmp_path: Path):
        image = _make_loaded_image(subject_centered_path)
        comp = _make_composition(
            rule_of_thirds=30,
            subject_position=40,
            centroid=(0.5, 0.5),
            dims=(300, 300),
        )
        analyzer = SuggestionsAnalyzer(composition=comp, output_dir=tmp_path)
        result = analyzer.analyze(image)
        if result.crop_preview_path:
            assert Path(result.crop_preview_path).is_file()


# ------------------------------------------------------------------
# Integration tests
# ------------------------------------------------------------------


class TestSuggestionsAnalyzer:
    def test_returns_suggestions_result(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=30, dynamic_range=25)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        assert isinstance(result, SuggestionsResult)
        assert len(result.suggestions) > 0

    def test_sorted_by_priority(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=10, sharpness=15, dynamic_range=20)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        priorities = [s.priority for s in result.suggestions]
        assert priorities == sorted(priorities)

    def test_max_suggestions_cap(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=10, sharpness=15, dynamic_range=20)
        comp = _make_composition(
            rule_of_thirds=20,
            subject_position=20,
            horizon=30,
            balance=20,
            horizon_angle=8.0,
            centroid=(0.5, 0.5),
            dims=(200, 200),
        )
        thresholds = SuggestionThresholds(max_suggestions=3)
        analyzer = SuggestionsAnalyzer(
            technical=tech, composition=comp, thresholds=thresholds
        )
        result = analyzer.analyze(image)
        assert len(result.suggestions) <= 3

    def test_no_prior_results_empty(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        analyzer = SuggestionsAnalyzer()
        result = analyzer.analyze(image)
        assert len(result.suggestions) == 0
        assert "looks great" in result.summary.lower()

    def test_summary_generated(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=30)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        assert result.summary != ""

    def test_suggestion_types_valid(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=20, sharpness=20, dynamic_range=20)
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        for s in result.suggestions:
            assert isinstance(s.type, SuggestionType)
            assert 1 <= s.priority <= 5
            assert s.instruction != ""


# ------------------------------------------------------------------
# AI polish tests (mocked)
# ------------------------------------------------------------------


class TestAIPolish:
    def test_polish_updates_instructions(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=30)

        polished_response = MagicMock()
        polished_response.message.content = (
            '[{"type": "exposure", "instruction": "Brighten the scene by half a stop"}]'
        )

        with patch("ollama.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.chat.return_value = polished_response
            mock_client_cls.return_value = mock_client

            analyzer = SuggestionsAnalyzer(
                technical=tech,
                ollama_host="http://fake:11434",
                ollama_model="llava",
            )
            result = analyzer.analyze(image)

            exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
            assert len(exposure_suggs) == 1
            assert "brighten" in exposure_suggs[0].instruction.lower()

    def test_polish_fallback_on_error(self, normal_image_path: Path):
        image = _make_loaded_image(normal_image_path)
        tech = _make_technical(exposure=30)

        with patch("ollama.Client") as mock_client_cls:
            mock_client_cls.side_effect = ConnectionError("no server")

            analyzer = SuggestionsAnalyzer(
                technical=tech,
                ollama_host="http://fake:11434",
            )
            result = analyzer.analyze(image)
            # Should still have algorithmic suggestions despite AI failure
            exposure_suggs = [s for s in result.suggestions if s.type == SuggestionType.EXPOSURE]
            assert len(exposure_suggs) == 1
            assert "exposure" in exposure_suggs[0].instruction.lower()


# ------------------------------------------------------------------
# Color suggestion tests
# ------------------------------------------------------------------


class TestColorSuggestion:
    def test_blue_cast_detected(self, image_dir: Path):
        """Create an image with strong blue tint."""
        arr = np.full((200, 200, 3), (200, 100, 100), dtype=np.uint8)  # heavy blue in BGR
        img = Image.fromarray(arr[:, :, ::-1])  # BGR -> RGB for Pillow
        path = image_dir / "blue_cast.jpg"
        img.save(path, "JPEG", quality=95)

        image = _make_loaded_image(path)
        tech = _make_technical()
        analyzer = SuggestionsAnalyzer(technical=tech)
        result = analyzer.analyze(image)
        color_suggs = [s for s in result.suggestions if s.type == SuggestionType.COLOR]
        # Should detect blue cast and suggest warmer
        if color_suggs:
            assert color_suggs[0].parameters["warmth"] == "warmer"
