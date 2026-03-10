from __future__ import annotations

import numpy as np

from visionscore.models import (
    AutoEditResult,
    CropSuggestion,
    ImprovementSuggestion,
    SuggestionType,
)
from visionscore.pipeline.auto_edit import (
    apply_color,
    apply_contrast,
    apply_crop,
    apply_exposure,
    apply_horizon,
    apply_sharpness,
    auto_edit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mean_luminance(bgr: np.ndarray) -> float:
    import cv2

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def _make_bgr(r: int, g: int, b: int, size: int = 200) -> np.ndarray:
    """Create a uniform BGR image."""
    img = np.full((size, size, 3), (b, g, r), dtype=np.uint8)
    return img


# ---------------------------------------------------------------------------
# apply_exposure
# ---------------------------------------------------------------------------


class TestApplyExposure:
    def test_brighten_increases_luminance(self) -> None:
        dark = _make_bgr(30, 30, 30)
        result = apply_exposure(dark, stops=1.0, direction="increase")
        assert _mean_luminance(result) > _mean_luminance(dark)

    def test_darken_decreases_luminance(self) -> None:
        bright = _make_bgr(220, 220, 220)
        result = apply_exposure(bright, stops=1.0, direction="decrease")
        assert _mean_luminance(result) < _mean_luminance(bright)

    def test_output_shape_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_exposure(img, stops=0.5, direction="increase")
        assert result.shape == img.shape

    def test_half_stop_less_aggressive_than_full(self) -> None:
        dark = _make_bgr(50, 50, 50)
        half = apply_exposure(dark, stops=0.5, direction="increase")
        full = apply_exposure(dark, stops=1.0, direction="increase")
        assert _mean_luminance(half) < _mean_luminance(full)


# ---------------------------------------------------------------------------
# apply_contrast
# ---------------------------------------------------------------------------


class TestApplyContrast:
    def test_stretch_expands_range(self) -> None:
        # Narrow-range image: all pixels in 100-150 range
        img = np.full((100, 100, 3), 125, dtype=np.uint8)
        img[:50, :] = 100
        img[50:, :] = 150
        result = apply_contrast(img, black_point=100, white_point=150)
        # After stretch, dark pixels should be near 0, bright near 255
        assert result.min() < 10
        assert result.max() > 245

    def test_identity_with_full_range(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_contrast(img, black_point=0, white_point=255)
        np.testing.assert_array_equal(result, img)

    def test_invalid_range_returns_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_contrast(img, black_point=200, white_point=100)
        np.testing.assert_array_equal(result, img)


# ---------------------------------------------------------------------------
# apply_sharpness
# ---------------------------------------------------------------------------


class TestApplySharpness:
    def test_increases_laplacian_variance(self) -> None:
        import cv2

        # Create a slightly blurry image
        img = _make_bgr(128, 128, 128, size=200)
        # Add some edges
        img[80:120, 80:120] = (255, 255, 255)
        blurred = cv2.GaussianBlur(img, (5, 5), 1.5)

        sharpened = apply_sharpness(blurred, usm_amount_pct=150, usm_radius_px=1.5, usm_threshold=0)

        var_before = cv2.Laplacian(cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        var_after = cv2.Laplacian(cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        assert var_after > var_before

    def test_output_shape_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_sharpness(img, usm_amount_pct=100, usm_radius_px=1.0, usm_threshold=2)
        assert result.shape == img.shape
        assert result.dtype == np.uint8


# ---------------------------------------------------------------------------
# apply_horizon
# ---------------------------------------------------------------------------


class TestApplyHorizon:
    def test_rotation_changes_size(self) -> None:
        img = np.full((300, 400, 3), 128, dtype=np.uint8)
        result = apply_horizon(img, rotate_degrees=5.0, direction="counterclockwise")
        # Auto-crop should produce a smaller image
        assert result.shape[0] < img.shape[0]
        assert result.shape[1] < img.shape[1]

    def test_tiny_angle_returns_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_horizon(img, rotate_degrees=0.05, direction="clockwise")
        np.testing.assert_array_equal(result, img)

    def test_no_black_borders(self) -> None:
        img = np.full((300, 400, 3), 128, dtype=np.uint8)
        result = apply_horizon(img, rotate_degrees=3.0, direction="clockwise")
        # Corners should not be black (all-zero)
        corners = [
            result[0, 0],
            result[0, -1],
            result[-1, 0],
            result[-1, -1],
        ]
        for corner in corners:
            assert corner.sum() > 0, "Black border pixel found at corner"


# ---------------------------------------------------------------------------
# apply_crop
# ---------------------------------------------------------------------------


class TestApplyCrop:
    def test_output_dimensions(self) -> None:
        img = np.full((400, 600, 3), 128, dtype=np.uint8)
        crop = CropSuggestion(target_x=50, target_y=50, target_w=200, target_h=150)
        result = apply_crop(img, crop, scale_x=1.0, scale_y=1.0)
        assert result.shape == (150, 200, 3)

    def test_scaling_from_resized_space(self) -> None:
        img = np.full((800, 1200, 3), 128, dtype=np.uint8)
        # Crop defined in half-size space
        crop = CropSuggestion(target_x=25, target_y=25, target_w=100, target_h=75)
        result = apply_crop(img, crop, scale_x=2.0, scale_y=2.0)
        assert result.shape == (150, 200, 3)

    def test_clamps_to_bounds(self) -> None:
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        crop = CropSuggestion(target_x=80, target_y=80, target_w=200, target_h=200)
        result = apply_crop(img, crop, scale_x=1.0, scale_y=1.0)
        # Should not exceed image bounds
        assert result.shape[0] <= 100
        assert result.shape[1] <= 100


# ---------------------------------------------------------------------------
# apply_color
# ---------------------------------------------------------------------------


class TestApplyColor:
    def test_corrects_blue_cast(self) -> None:
        import cv2

        # Image with blue cast: high B channel in LAB
        blue_img = _make_bgr(100, 100, 180)
        lab = cv2.cvtColor(blue_img, cv2.COLOR_BGR2LAB)
        mean_b_before = float(lab[:, :, 2].mean())

        result = apply_color(blue_img, mean_a=128.0, mean_b=mean_b_before)
        lab_after = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
        mean_b_after = float(lab_after[:, :, 2].mean())

        # Should move closer to 128
        assert abs(mean_b_after - 128) < abs(mean_b_before - 128)

    def test_neutral_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result = apply_color(img, mean_a=128.0, mean_b=128.0)
        np.testing.assert_array_equal(result, img)


# ---------------------------------------------------------------------------
# auto_edit orchestration
# ---------------------------------------------------------------------------


class TestAutoEdit:
    def test_composition_skipped(self) -> None:
        img = _make_bgr(128, 128, 128)
        suggestions = [
            ImprovementSuggestion(
                type=SuggestionType.COMPOSITION,
                instruction="Reframe the shot",
                parameters={"balance_score": 30.0, "deficit": 10.0, "heavy_side": "left"},
            )
        ]
        _, applied, skipped = auto_edit(img, suggestions)
        assert len(applied) == 0
        assert len(skipped) == 1
        assert "composition" in skipped[0].lower()

    def test_no_suggestions_unchanged(self) -> None:
        img = _make_bgr(128, 128, 128)
        result, applied, skipped = auto_edit(img, [])
        np.testing.assert_array_equal(result, img)
        assert len(applied) == 0
        assert len(skipped) == 0

    def test_edit_order_respected(self) -> None:
        img = np.full((400, 600, 3), 100, dtype=np.uint8)
        suggestions = [
            ImprovementSuggestion(
                type=SuggestionType.SHARPNESS,
                instruction="Sharpen",
                parameters={"usm_amount_pct": 100, "usm_radius_px": 1.0, "usm_threshold": 2},
            ),
            ImprovementSuggestion(
                type=SuggestionType.EXPOSURE,
                instruction="Brighten",
                parameters={"stops": 0.5, "direction": "increase"},
            ),
        ]
        _, applied, _ = auto_edit(img, suggestions)
        types = [e.type for e in applied]
        # Exposure should come before sharpness per _EDIT_ORDER
        assert types.index(SuggestionType.EXPOSURE) < types.index(SuggestionType.SHARPNESS)

    def test_multiple_edits_applied(self) -> None:
        img = _make_bgr(80, 80, 80, size=200)
        suggestions = [
            ImprovementSuggestion(
                type=SuggestionType.EXPOSURE,
                instruction="Brighten",
                parameters={"stops": 1.0, "direction": "increase"},
            ),
            ImprovementSuggestion(
                type=SuggestionType.CONTRAST,
                instruction="Boost contrast",
                parameters={"black_point": 20, "white_point": 235},
            ),
        ]
        result, applied, _ = auto_edit(img, suggestions)
        assert len(applied) == 2
        assert not np.array_equal(result, img)


# ---------------------------------------------------------------------------
# run_auto_edit (integration)
# ---------------------------------------------------------------------------


class TestRunAutoEdit:
    def test_produces_output_file(self, normal_image_path, tmp_path) -> None:
        from visionscore.pipeline.auto_edit import run_auto_edit

        output = tmp_path / "fixed.jpg"
        result = run_auto_edit(normal_image_path, output_path=output, skip_ai=True)

        assert isinstance(result, AutoEditResult)
        assert result.edit_time_seconds > 0
        # If edits were applied, file should exist
        if result.applied_edits:
            assert output.exists()

    def test_result_model_populated(self, dark_image_path, tmp_path) -> None:
        from visionscore.pipeline.auto_edit import run_auto_edit

        output = tmp_path / "fixed_dark.jpg"
        result = run_auto_edit(dark_image_path, output_path=output, skip_ai=True)

        assert isinstance(result, AutoEditResult)
        assert result.original_path == str(dark_image_path)
        # Dark image should trigger at least an exposure suggestion
        if result.applied_edits:
            types = [e.type for e in result.applied_edits]
            assert all(isinstance(t, SuggestionType) for t in types)
