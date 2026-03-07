from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from visionscore.analyzers.composition import CompositionAnalyzer
from visionscore.models import CompositionScore
from visionscore.pipeline.loader import LoadedImage, load_image


@pytest.fixture
def analyzer() -> CompositionAnalyzer:
    return CompositionAnalyzer()


class TestSaliencyDetection:
    def test_bright_subject_detected_near_power_point(
        self, analyzer: CompositionAnalyzer, subject_at_power_point_path: Path
    ):
        image = load_image(subject_at_power_point_path)
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)
        centroid, _bbox, _sal = analyzer._detect_saliency(gray)
        assert abs(centroid[0] - 1 / 3) < 0.15
        assert abs(centroid[1] - 1 / 3) < 0.15

    def test_uniform_image_returns_center(
        self, analyzer: CompositionAnalyzer, flat_gray_image_path: Path
    ):
        image = load_image(flat_gray_image_path)
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)
        centroid, _bbox, _sal = analyzer._detect_saliency(gray)
        assert abs(centroid[0] - 0.5) < 0.1
        assert abs(centroid[1] - 0.5) < 0.1

    def test_saliency_map_shape_matches_input(
        self, analyzer: CompositionAnalyzer, normal_image_path: Path
    ):
        image = load_image(normal_image_path)
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)
        _, _, saliency_map = analyzer._detect_saliency(gray)
        assert saliency_map.shape == gray.shape

    def test_saliency_map_values_normalized(
        self, analyzer: CompositionAnalyzer, normal_image_path: Path
    ):
        image = load_image(normal_image_path)
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)
        _, _, saliency_map = analyzer._detect_saliency(gray)
        assert saliency_map.min() >= 0.0
        assert saliency_map.max() <= 1.0 + 1e-6


class TestRuleOfThirds:
    def test_exact_power_point_scores_near_100(self, analyzer: CompositionAnalyzer):
        score = analyzer._analyze_rule_of_thirds((1 / 3, 1 / 3))
        assert score > 95

    def test_subject_at_power_point_scores_high(
        self, analyzer: CompositionAnalyzer, subject_at_power_point_path: Path
    ):
        result = analyzer.analyze(load_image(subject_at_power_point_path))
        assert result.rule_of_thirds > 65

    def test_subject_centered_scores_moderate(
        self, analyzer: CompositionAnalyzer, subject_centered_path: Path
    ):
        result = analyzer.analyze(load_image(subject_centered_path))
        assert 25 < result.rule_of_thirds < 80

    def test_corner_scores_low(self, analyzer: CompositionAnalyzer):
        score = analyzer._analyze_rule_of_thirds((0.0, 0.0))
        assert score < 40


class TestHorizon:
    def test_no_horizon_returns_neutral(
        self, analyzer: CompositionAnalyzer, flat_gray_image_path: Path
    ):
        result = analyzer.analyze(load_image(flat_gray_image_path))
        assert 70 <= result.horizon <= 80

    def test_tilted_horizon_scores_low(
        self, analyzer: CompositionAnalyzer, tilted_horizon_path: Path
    ):
        result = analyzer.analyze(load_image(tilted_horizon_path))
        assert result.horizon < 80

    def test_level_horizon_scores_high(self, analyzer: CompositionAnalyzer):
        arr = np.zeros((300, 400, 3), dtype=np.uint8)
        arr[:150, :] = (230, 200, 180)
        arr[150:, :] = (60, 120, 80)
        dummy = LoadedImage(
            original=arr,
            resized=arr,
            path=Path("test.jpg"),
            format="JPEG",
            width=400,
            height=300,
        )
        result = analyzer.analyze(dummy)
        assert result.horizon >= 70


class TestBalance:
    def test_symmetric_image_scores_high(
        self, analyzer: CompositionAnalyzer, balanced_image_path: Path
    ):
        result = analyzer.analyze(load_image(balanced_image_path))
        assert result.balance > 60

    def test_asymmetric_image_scores_lower(
        self,
        analyzer: CompositionAnalyzer,
        unbalanced_image_path: Path,
        balanced_image_path: Path,
    ):
        result = analyzer.analyze(load_image(unbalanced_image_path))
        balanced_result = analyzer.analyze(load_image(balanced_image_path))
        assert result.balance < balanced_result.balance


class TestOverallComposition:
    def test_returns_composition_score_model(
        self, analyzer: CompositionAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        assert isinstance(result, CompositionScore)

    def test_overall_is_weighted_combination(
        self, analyzer: CompositionAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        expected = round(
            result.rule_of_thirds * 0.40
            + result.subject_position * 0.25
            + result.horizon * 0.20
            + result.balance * 0.15,
            1,
        )
        assert abs(result.overall - expected) < 0.2

    def test_all_scores_in_valid_range(
        self, analyzer: CompositionAnalyzer, normal_image_path: Path
    ):
        result = analyzer.analyze(load_image(normal_image_path))
        for field in ["rule_of_thirds", "subject_position", "horizon", "balance", "overall"]:
            score = getattr(result, field)
            assert 0 <= score <= 100, f"{field} out of range: {score}"
