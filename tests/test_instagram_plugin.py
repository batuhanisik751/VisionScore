from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from visionscore.pipeline.loader import LoadedImage
from visionscore.plugins.info import PluginInfo
from visionscore.plugins.instagram import (
    InstagramReadinessAnalyzer,
    InstagramReadinessResult,
)


# -- helpers --

def _make_loaded_image(
    width: int,
    height: int,
    saturation: int = 100,
) -> LoadedImage:
    """Build a LoadedImage from a synthetic BGR array."""
    # Create a solid-colour image with controllable saturation via HSV
    hsv = np.full((height, width, 3), (90, saturation, 180), dtype=np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return LoadedImage(
        original=bgr,
        resized=bgr,
        path=Path("synthetic.jpg"),
        format="JPEG",
        width=width,
        height=height,
    )


# -- tests --

class TestInstagramReadinessAnalyzer:
    def test_returns_correct_result_type(self) -> None:
        analyzer = InstagramReadinessAnalyzer()
        image = _make_loaded_image(1080, 1080)
        result = analyzer.analyze(image)
        assert isinstance(result, InstagramReadinessResult)

    def test_square_image_high_aspect_score(self) -> None:
        analyzer = InstagramReadinessAnalyzer()
        image = _make_loaded_image(1080, 1080)
        result = analyzer.analyze(image)
        assert result.aspect_ratio_score >= 95.0

    def test_very_wide_image_penalized(self) -> None:
        analyzer = InstagramReadinessAnalyzer()
        image = _make_loaded_image(4000, 1000)  # 4:1 ratio
        result = analyzer.analyze(image)
        # 4:1 is way wider than Instagram's 1.91:1 limit
        assert result.aspect_ratio_score < 60.0

    def test_low_resolution_penalized(self) -> None:
        analyzer = InstagramReadinessAnalyzer()
        image = _make_loaded_image(200, 200)
        result = analyzer.analyze(image)
        assert result.resolution_score < 30.0

    def test_high_resolution_full_score(self) -> None:
        analyzer = InstagramReadinessAnalyzer()
        image = _make_loaded_image(1080, 1080)
        result = analyzer.analyze(image)
        assert result.resolution_score == 100.0

    def test_plugin_info_set(self) -> None:
        assert InstagramReadinessAnalyzer.plugin_info is not None
        assert isinstance(InstagramReadinessAnalyzer.plugin_info, PluginInfo)
        assert InstagramReadinessAnalyzer.plugin_info.name == "instagram_readiness"
