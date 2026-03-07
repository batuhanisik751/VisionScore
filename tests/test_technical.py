from __future__ import annotations

from pathlib import Path

from visionscore.analyzers.technical import TechnicalAnalyzer
from visionscore.models import TechnicalScore
from visionscore.pipeline.loader import load_image

import pytest


@pytest.fixture
def analyzer() -> TechnicalAnalyzer:
    return TechnicalAnalyzer()


class TestSharpness:
    def test_sharp_image_scores_high(self, analyzer: TechnicalAnalyzer, sharp_image_path: Path):
        result = analyzer.analyze(load_image(sharp_image_path))
        assert result.sharpness > 70

    def test_blurry_image_scores_low(self, analyzer: TechnicalAnalyzer, blurry_image_path: Path):
        result = analyzer.analyze(load_image(blurry_image_path))
        assert result.sharpness < 30


class TestExposure:
    def test_normal_exposure_scores_high(
        self, analyzer: TechnicalAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        assert result.exposure > 90

    def test_bright_image_scores_low(self, analyzer: TechnicalAnalyzer, bright_image_path: Path):
        result = analyzer.analyze(load_image(bright_image_path))
        assert result.exposure < 30


class TestNoise:
    def test_clean_image_scores_high(self, analyzer: TechnicalAnalyzer, normal_image_path: Path):
        result = analyzer.analyze(load_image(normal_image_path))
        assert result.noise > 80

    def test_noisy_image_scores_low(self, analyzer: TechnicalAnalyzer, noisy_image_path: Path):
        result = analyzer.analyze(load_image(noisy_image_path))
        assert result.noise < 40


class TestDynamicRange:
    def test_gradient_scores_high(self, analyzer: TechnicalAnalyzer, normal_image_path: Path):
        result = analyzer.analyze(load_image(normal_image_path))
        assert result.dynamic_range > 80

    def test_flat_gray_scores_low(self, analyzer: TechnicalAnalyzer, flat_gray_image_path: Path):
        result = analyzer.analyze(load_image(flat_gray_image_path))
        assert result.dynamic_range < 40


class TestOverallScore:
    def test_returns_technical_score_model(
        self, analyzer: TechnicalAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        assert isinstance(result, TechnicalScore)

    def test_overall_is_weighted_combination(
        self, analyzer: TechnicalAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        expected = round(
            result.sharpness * 0.35
            + result.exposure * 0.30
            + result.noise * 0.20
            + result.dynamic_range * 0.15,
            1,
        )
        assert abs(result.overall - expected) < 0.2

    def test_all_scores_in_valid_range(self, analyzer: TechnicalAnalyzer, normal_image_path: Path):
        result = analyzer.analyze(load_image(normal_image_path))
        for field in ["sharpness", "exposure", "noise", "dynamic_range", "overall"]:
            score = getattr(result, field)
            assert 0 <= score <= 100, f"{field} out of range: {score}"

    def test_dark_image_overall_low(self, analyzer: TechnicalAnalyzer, dark_image_path: Path):
        result = analyzer.analyze(load_image(dark_image_path))
        assert result.overall < 50
