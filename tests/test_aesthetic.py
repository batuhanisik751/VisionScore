from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from visionscore.analyzers.aesthetic import AestheticAnalyzer, NIMAModel
from visionscore.models import AestheticScore
from visionscore.pipeline.loader import load_image


@pytest.fixture
def analyzer(tmp_path: Path) -> AestheticAnalyzer:
    """AestheticAnalyzer with a real (untrained) model saved to tmp_path."""
    model = NIMAModel()
    weights_path = tmp_path / "nima_mobilenetv2.pth"
    torch.save(model.state_dict(), weights_path)
    return AestheticAnalyzer(model_path=weights_path, device="cpu")


def _make_distribution(peak: int, sharpness: float = 50.0) -> torch.Tensor:
    """Create a peaked probability distribution over 10 buckets."""
    logits = torch.zeros(1, 10)
    for i in range(10):
        logits[0, i] = -sharpness * (i - peak) ** 2
    return torch.softmax(logits, dim=1)


class TestModelArchitecture:
    def test_output_shape(self):
        model = NIMAModel()
        model.eval()
        x = torch.randn(1, 3, 224, 224)
        with torch.inference_mode():
            out = model(x)
        assert out.shape == (1, 10)

    def test_output_is_probability_distribution(self):
        model = NIMAModel()
        model.eval()
        x = torch.randn(1, 3, 224, 224)
        with torch.inference_mode():
            out = model(x)
        assert torch.all(out >= 0)
        assert abs(out.sum().item() - 1.0) < 1e-5


class TestPreprocessing:
    def test_output_shape(self):
        analyzer = AestheticAnalyzer(device="cpu")
        bgr = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        tensor = analyzer._preprocess(bgr)
        assert tensor.shape == (1, 3, 224, 224)

    def test_handles_different_sizes(self):
        analyzer = AestheticAnalyzer(device="cpu")
        for size in [(50, 50, 3), (1000, 500, 3)]:
            bgr = np.random.randint(0, 255, size, dtype=np.uint8)
            tensor = analyzer._preprocess(bgr)
            assert tensor.shape == (1, 3, 224, 224)

    def test_normalizes_values(self):
        analyzer = AestheticAnalyzer(device="cpu")
        bgr = np.full((200, 200, 3), 128, dtype=np.uint8)
        tensor = analyzer._preprocess(bgr)
        assert tensor.min().item() > -3.0
        assert tensor.max().item() < 3.0


class TestScoreDistribution:
    def test_uniform_gives_midrange(self):
        dist = torch.ones(1, 10) / 10.0
        score, std_dev, confidence = AestheticAnalyzer._distribution_to_score(dist)
        assert 45 < score < 65

    def test_peaked_high_gives_high_score(self):
        dist = _make_distribution(peak=9)  # peaked at bucket 10 (index 9)
        score, _, _ = AestheticAnalyzer._distribution_to_score(dist)
        assert score > 80

    def test_peaked_low_gives_low_score(self):
        dist = _make_distribution(peak=0)  # peaked at bucket 1 (index 0)
        score, _, _ = AestheticAnalyzer._distribution_to_score(dist)
        assert score < 20

    def test_confidence_high_for_peaked(self):
        dist = _make_distribution(peak=5, sharpness=100.0)
        _, _, confidence = AestheticAnalyzer._distribution_to_score(dist)
        assert confidence > 0.7

    def test_confidence_low_for_flat(self):
        dist = torch.ones(1, 10) / 10.0
        _, _, confidence = AestheticAnalyzer._distribution_to_score(dist)
        assert confidence < 0.5

    def test_std_dev_low_for_peaked(self):
        dist = _make_distribution(peak=5, sharpness=100.0)
        _, std_dev, _ = AestheticAnalyzer._distribution_to_score(dist)
        assert std_dev < 1.0

    def test_std_dev_high_for_flat(self):
        dist = torch.ones(1, 10) / 10.0
        _, std_dev, _ = AestheticAnalyzer._distribution_to_score(dist)
        assert std_dev > 2.0


class TestAestheticAnalyzer:
    def test_returns_aesthetic_score(self, analyzer: AestheticAnalyzer, sharp_image_path: Path):
        image = load_image(sharp_image_path)
        result = analyzer.analyze(image)
        assert isinstance(result, AestheticScore)

    def test_scores_in_valid_range(self, analyzer: AestheticAnalyzer, sharp_image_path: Path):
        image = load_image(sharp_image_path)
        result = analyzer.analyze(image)
        assert 0 <= result.nima_score <= 100
        assert 0 <= result.confidence <= 1
        assert 0 <= result.std_dev <= 5.0
        assert 0 <= result.overall <= 100

    def test_missing_weights_raises(self):
        from visionscore.pipeline.loader import LoadedImage

        analyzer = AestheticAnalyzer(model_path=Path("/nonexistent/model.pth"), device="cpu")
        bgr = np.zeros((100, 100, 3), dtype=np.uint8)
        dummy = LoadedImage(
            original=bgr, resized=bgr, path=Path("test.jpg"),
            format="JPEG", width=100, height=100,
        )
        with pytest.raises(FileNotFoundError, match="NIMA weights not found"):
            analyzer.analyze(dummy)

    def test_model_cached_across_calls(self, analyzer: AestheticAnalyzer, sharp_image_path: Path):
        image = load_image(sharp_image_path)
        analyzer.analyze(image)
        first_model = analyzer._model
        analyzer.analyze(image)
        assert analyzer._model is first_model


class TestDeviceDetection:
    def test_auto_selects_cpu_when_no_gpu(self):
        with patch("torch.cuda.is_available", return_value=False), \
             patch("torch.backends.mps.is_available", return_value=False):
            analyzer = AestheticAnalyzer(device="auto")
            assert analyzer._device == torch.device("cpu")

    def test_explicit_device_honored(self):
        analyzer = AestheticAnalyzer(device="cpu")
        assert analyzer._device == torch.device("cpu")
