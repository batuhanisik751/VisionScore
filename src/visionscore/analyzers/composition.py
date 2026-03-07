from __future__ import annotations

import math

import cv2
import numpy as np

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.models import CompositionScore, ImageMeta
from visionscore.pipeline.loader import LoadedImage

# Rule of thirds power points (normalized 0-1)
_POWER_POINTS = [
    (1 / 3, 1 / 3),
    (2 / 3, 1 / 3),
    (1 / 3, 2 / 3),
    (2 / 3, 2 / 3),
]
_MAX_POWER_DIST = math.sqrt((2 / 3) ** 2 + (2 / 3) ** 2)


class CompositionAnalyzer(BaseAnalyzer):
    """Evaluate spatial composition using saliency detection and rule-based analysis."""

    RULE_OF_THIRDS_WEIGHT = 0.40
    SUBJECT_POSITION_WEIGHT = 0.25
    HORIZON_WEIGHT = 0.20
    BALANCE_WEIGHT = 0.15

    _NEUTRAL_HORIZON_SCORE = 75.0

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> CompositionScore:
        gray = cv2.cvtColor(image.resized, cv2.COLOR_BGR2GRAY)
        centroid, _bbox, saliency_map = self._detect_saliency(gray)

        rule_of_thirds = self._analyze_rule_of_thirds(centroid)
        subject_position = self._analyze_subject_position(centroid, saliency_map)
        horizon = self._analyze_horizon(gray)
        balance = self._analyze_balance(image.resized)

        overall = (
            rule_of_thirds * self.RULE_OF_THIRDS_WEIGHT
            + subject_position * self.SUBJECT_POSITION_WEIGHT
            + horizon * self.HORIZON_WEIGHT
            + balance * self.BALANCE_WEIGHT
        )

        return CompositionScore(
            rule_of_thirds=round(rule_of_thirds, 1),
            subject_position=round(subject_position, 1),
            horizon=round(horizon, 1),
            balance=round(balance, 1),
            overall=round(overall, 1),
        )

    # ------------------------------------------------------------------
    # Saliency detection (spectral residual method)
    # ------------------------------------------------------------------

    def _detect_saliency(
        self, gray: np.ndarray
    ) -> tuple[tuple[float, float], tuple[int, int, int, int], np.ndarray]:
        """Detect salient region using spectral residual FFT.

        Returns:
            centroid: (x, y) normalized to [0, 1]
            bbox: (x, y, w, h) in pixel coordinates
            saliency_map: float32 array [0, 1], same shape as input
        """
        h, w = gray.shape

        # Resize to small fixed size for FFT, then scale back
        small = cv2.resize(gray, (64, 64)).astype(np.float64)
        fft = np.fft.fft2(small)
        amplitude = np.abs(fft)
        phase = np.angle(fft)
        log_amp = np.log1p(amplitude)
        smoothed = cv2.blur(log_amp, (3, 3))
        spectral_residual = log_amp - smoothed
        saliency_small = np.abs(np.fft.ifft2(np.exp(spectral_residual + 1j * phase))) ** 2
        saliency_small = cv2.GaussianBlur(saliency_small.astype(np.float32), (5, 5), 2.5)

        # Scale back to original size
        saliency = cv2.resize(saliency_small, (w, h))
        s_min, s_max = saliency.min(), saliency.max()
        if s_max - s_min > 1e-8:
            saliency = (saliency - s_min) / (s_max - s_min)
        else:
            saliency = np.zeros_like(saliency)

        # If saliency map has very low contrast, no real subject exists
        if saliency.std() < 0.05:
            return (0.5, 0.5), (0, 0, w, h), saliency

        # Threshold and find contours
        thresh_val = saliency.mean() + saliency.std()
        binary = (saliency > thresh_val).astype(np.uint8) * 255
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return (0.5, 0.5), (0, 0, w, h), saliency

        largest = max(contours, key=cv2.contourArea)
        x, y, bw, bh = cv2.boundingRect(largest)
        moments = cv2.moments(largest)
        if moments["m00"] > 0:
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
        else:
            cx, cy = x + bw / 2, y + bh / 2

        return (cx / w, cy / h), (x, y, bw, bh), saliency

    # ------------------------------------------------------------------
    # Rule of thirds
    # ------------------------------------------------------------------

    def _analyze_rule_of_thirds(self, centroid: tuple[float, float]) -> float:
        """Score how close the subject centroid is to a power point."""
        min_dist = min(
            math.sqrt((centroid[0] - px) ** 2 + (centroid[1] - py) ** 2)
            for px, py in _POWER_POINTS
        )
        return max(0.0, min(100.0, 100.0 * (1.0 - (min_dist / _MAX_POWER_DIST) ** 0.7)))

    # ------------------------------------------------------------------
    # Subject position (prominence + edge avoidance)
    # ------------------------------------------------------------------

    def _analyze_subject_position(
        self, centroid: tuple[float, float], saliency_map: np.ndarray
    ) -> float:
        """Score subject prominence and framing."""
        # Prominence: ratio of salient pixels, ideal 5-40%, peak ~17%
        thresh = saliency_map.mean() + saliency_map.std()
        salient_ratio = float((saliency_map > thresh).sum()) / saliency_map.size
        ideal = 0.17
        prominence = max(0.0, 100.0 * math.exp(-((salient_ratio - ideal) ** 2) / (2 * 0.12**2)))

        # Edge avoidance: penalize centroid within 5% of any edge
        margin = 0.05
        cx, cy = centroid
        edge_penalty = 0.0
        if cx < margin or cx > 1 - margin:
            edge_penalty += 50.0
        if cy < margin or cy > 1 - margin:
            edge_penalty += 50.0
        edge_score = max(0.0, 100.0 - edge_penalty)

        return 0.5 * prominence + 0.5 * edge_score

    # ------------------------------------------------------------------
    # Horizon detection
    # ------------------------------------------------------------------

    def _analyze_horizon(self, gray: np.ndarray) -> float:
        """Detect horizon line and score its levelness."""
        h, w = gray.shape
        median_val = float(np.median(gray))
        low = max(0, int(0.66 * median_val))
        high = min(255, int(1.33 * median_val))
        if high - low < 20:
            low, high = 50, 150
        edges = cv2.Canny(gray, low, high)

        min_length = int(0.30 * w)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=min_length, maxLineGap=15)

        if lines is None:
            return self._NEUTRAL_HORIZON_SCORE

        best_angle: float | None = None
        best_length = 0

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(angle) > 15.0:
                continue
            length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length > best_length:
                best_length = length
                best_angle = angle

        if best_angle is None:
            return self._NEUTRAL_HORIZON_SCORE

        abs_angle = abs(best_angle)
        if abs_angle <= 3.0:
            penalty = abs_angle * 10.0
        else:
            penalty = 30.0 + (abs_angle - 3.0) * 5.0

        return max(0.0, min(100.0, 100.0 - penalty))

    # ------------------------------------------------------------------
    # Visual balance
    # ------------------------------------------------------------------

    def _analyze_balance(self, image_bgr: np.ndarray) -> float:
        """Score visual balance by comparing halves."""
        lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
        lum = lab[:, :, 0].astype(np.float64)
        edges = cv2.Canny(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY), 50, 150)

        h, w = lum.shape
        mid_x, mid_y = w // 2, h // 2

        # Luminance differences
        mean_all = lum.mean() or 1.0
        lum_diff_lr = abs(lum[:, :mid_x].mean() - lum[:, mid_x:].mean()) / mean_all
        lum_diff_tb = abs(lum[:mid_y, :].mean() - lum[mid_y:, :].mean()) / mean_all

        # Edge density differences
        edge_total = edges.sum() or 1.0
        edge_left = edges[:, :mid_x].sum() / edge_total
        edge_right = edges[:, mid_x:].sum() / edge_total
        edge_diff_lr = abs(edge_left - edge_right) * 2.0  # scale to ~0-1
        edge_top = edges[:mid_y, :].sum() / edge_total
        edge_bottom = edges[mid_y:, :].sum() / edge_total
        edge_diff_tb = abs(edge_top - edge_bottom) * 2.0

        imbalance = (
            0.3 * lum_diff_lr
            + 0.1 * lum_diff_tb
            + 0.3 * edge_diff_lr
            + 0.1 * edge_diff_tb
        )
        imbalance = min(1.0, imbalance)

        return max(0.0, min(100.0, 100.0 * (1.0 - imbalance) ** 1.5))
