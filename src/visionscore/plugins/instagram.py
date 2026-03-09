from __future__ import annotations

import cv2
import numpy as np
from pydantic import BaseModel, Field

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.models import ImageMeta
from visionscore.pipeline.loader import LoadedImage
from visionscore.plugins.info import PluginInfo


class InstagramReadinessResult(BaseModel):
    """Result from the Instagram Readiness analyzer."""

    aspect_ratio_score: float = Field(ge=0, le=100)
    resolution_score: float = Field(ge=0, le=100)
    saturation_score: float = Field(ge=0, le=100)
    recommended_crop: str = ""
    issues: list[str] = Field(default_factory=list)
    overall: float = Field(ge=0, le=100)


class InstagramReadinessAnalyzer(BaseAnalyzer):
    """Evaluate how well a photo fits Instagram's format and aesthetic preferences."""

    plugin_info = PluginInfo(
        name="instagram_readiness",
        display_name="Instagram Readiness",
        version="0.1.0",
        description="Evaluates photo fit for Instagram format and aesthetics",
        score_weight=0.0,
        score_field="overall",
    )

    # Instagram's preferred aspect ratios
    _IDEAL_RATIOS = {
        "square (1:1)": 1.0,
        "portrait (4:5)": 4.0 / 5.0,
        "landscape (1.91:1)": 1.91,
    }
    _MIN_DIMENSION = 1080

    def analyze(
        self, image: LoadedImage, metadata: ImageMeta | None = None
    ) -> InstagramReadinessResult:
        issues: list[str] = []
        w, h = image.width, image.height
        ratio = w / h if h > 0 else 1.0

        aspect_ratio_score = self._score_aspect_ratio(ratio, issues)
        resolution_score = self._score_resolution(w, h, issues)
        saturation_score = self._score_saturation(image)
        recommended_crop = self._recommend_crop(ratio)

        overall = round(
            0.40 * aspect_ratio_score + 0.30 * resolution_score + 0.30 * saturation_score,
            1,
        )

        return InstagramReadinessResult(
            aspect_ratio_score=round(aspect_ratio_score, 1),
            resolution_score=round(resolution_score, 1),
            saturation_score=round(saturation_score, 1),
            recommended_crop=recommended_crop,
            issues=issues,
            overall=overall,
        )

    def _score_aspect_ratio(self, ratio: float, issues: list[str]) -> float:
        # Instagram allows 4:5 (0.8) to 1.91:1
        if ratio < 0.8:
            issues.append("Too tall for Instagram (narrower than 4:5)")
            return max(0.0, 100.0 - (0.8 - ratio) * 200)
        if ratio > 1.91:
            issues.append("Too wide for Instagram (wider than 1.91:1)")
            return max(0.0, 100.0 - (ratio - 1.91) * 200)

        # Score based on distance from nearest ideal ratio
        min_dist = min(abs(ratio - ideal) for ideal in self._IDEAL_RATIOS.values())
        return max(0.0, min(100.0, 100.0 - min_dist * 100))

    def _score_resolution(self, w: int, h: int, issues: list[str]) -> float:
        min_dim = min(w, h)
        if min_dim >= self._MIN_DIMENSION:
            return 100.0
        if min_dim < 320:
            issues.append(f"Very low resolution ({w}x{h})")
            return 0.0
        issues.append(f"Below recommended 1080px minimum ({min_dim}px)")
        return round(min_dim / self._MIN_DIMENSION * 100, 1)

    def _score_saturation(self, image: LoadedImage) -> float:
        hsv = cv2.cvtColor(image.resized, cv2.COLOR_BGR2HSV)
        mean_sat = float(np.mean(hsv[:, :, 1]))
        # Scale: 0-255 saturation. Instagram favors moderate-to-high saturation.
        # ~80-150 is ideal range
        if mean_sat < 20:
            return 20.0
        if mean_sat > 200:
            return 70.0
        return min(100.0, mean_sat / 130.0 * 100.0)

    @staticmethod
    def _recommend_crop(ratio: float) -> str:
        if 0.95 <= ratio <= 1.05:
            return "Already square — ideal for Instagram"
        if ratio < 0.95:
            return "Crop to 4:5 portrait for best Instagram fit"
        if ratio <= 1.3:
            return "Crop to 1:1 square for best Instagram fit"
        return "Crop to 1.91:1 landscape for Instagram stories/feed"
