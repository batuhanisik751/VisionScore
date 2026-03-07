from __future__ import annotations

import math

import cv2
import numpy as np

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.config import Thresholds
from visionscore.models import ImageMeta, TechnicalScore
from visionscore.pipeline.loader import LoadedImage


class TechnicalAnalyzer(BaseAnalyzer):
    """Analyzes objective image quality: sharpness, exposure, noise, dynamic range."""

    SHARPNESS_WEIGHT = 0.35
    EXPOSURE_WEIGHT = 0.30
    NOISE_WEIGHT = 0.20
    DYNAMIC_RANGE_WEIGHT = 0.15

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.thresholds = thresholds or Thresholds()

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> TechnicalScore:
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)

        sharpness = self._analyze_sharpness(gray)
        exposure = self._analyze_exposure(image.resized)
        noise = self._analyze_noise(gray)
        dynamic_range = self._analyze_dynamic_range(gray)

        overall = (
            sharpness * self.SHARPNESS_WEIGHT
            + exposure * self.EXPOSURE_WEIGHT
            + noise * self.NOISE_WEIGHT
            + dynamic_range * self.DYNAMIC_RANGE_WEIGHT
        )

        return TechnicalScore(
            sharpness=round(sharpness, 1),
            exposure=round(exposure, 1),
            noise=round(noise, 1),
            dynamic_range=round(dynamic_range, 1),
            overall=round(overall, 1),
        )

    def _analyze_sharpness(self, gray: np.ndarray) -> float:
        """Sharpness via Laplacian variance (70%) + Sobel gradient magnitude (30%)."""
        # Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = float(laplacian.var())

        if variance < 1:
            lap_score = 0.0
        else:
            log_var = math.log(variance)
            log_thresh = math.log(self.thresholds.blur_threshold)
            x = (log_var - log_thresh) * 2.0
            lap_score = 100.0 / (1.0 + math.exp(-x))

        # Sobel gradient magnitude
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = float(np.sqrt(sobel_x**2 + sobel_y**2).mean())

        if magnitude < 0.1:
            sobel_score = 0.0
        else:
            log_mag = math.log(magnitude)
            x = (log_mag - math.log(20)) * 2.0
            sobel_score = 100.0 / (1.0 + math.exp(-x))

        score = 0.7 * lap_score + 0.3 * sobel_score
        return max(0.0, min(100.0, score))

    def _analyze_exposure(self, image_bgr: np.ndarray) -> float:
        """Exposure via LAB L-channel histogram analysis with clipping penalty."""
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0].astype(np.float64)

        mean_l = float(l_channel.mean())
        low = self.thresholds.exposure_low
        high = self.thresholds.exposure_high

        # Brightness score
        if low <= mean_l <= high:
            center = (low + high) / 2.0
            half_range = (high - low) / 2.0
            deviation = abs(mean_l - center) / half_range
            brightness_score = 100.0 * (1.0 - 0.3 * deviation)
        elif mean_l < low:
            brightness_score = max(0.0, 70.0 * (mean_l / low))
        else:
            brightness_score = max(0.0, 70.0 * ((255 - mean_l) / (255 - high)))

        # Clipping penalty
        total_pixels = l_channel.size
        clipped_low = np.sum(l_channel <= 5) / total_pixels
        clipped_high = np.sum(l_channel >= 250) / total_pixels
        clip_penalty = min(60.0, (clipped_low + clipped_high) * 120.0)

        score = max(0.0, brightness_score - clip_penalty)
        return max(0.0, min(100.0, score))

    def _analyze_noise(self, gray: np.ndarray) -> float:
        """Noise estimation via the Immerkaer method."""
        h, w = gray.shape

        kernel = np.array(
            [[1, -2, 1], [-2, 4, -2], [1, -2, 1]],
            dtype=np.float64,
        )

        convolved = cv2.filter2D(gray.astype(np.float64), -1, kernel)

        sigma = np.sum(np.abs(convolved)) * math.sqrt(math.pi / 2) / (6.0 * (w - 2) * (h - 2))

        if sigma < 0.01:
            return 100.0

        k = math.log(2) / self.thresholds.noise_threshold
        score = 100.0 * math.exp(-k * sigma)
        return max(0.0, min(100.0, score))

    def _analyze_dynamic_range(self, gray: np.ndarray) -> float:
        """Dynamic range via percentile-based tonal range utilization."""
        p2 = float(np.percentile(gray, 2))
        p98 = float(np.percentile(gray, 98))
        tonal_range = p98 - p2

        if tonal_range <= 0:
            return 0.0

        score = 100.0 * (tonal_range / 255.0) ** 0.8
        return max(0.0, min(100.0, score))
