from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

import cv2

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.config import SuggestionThresholds
from visionscore.models import (
    AIFeedback,
    CompositionScore,
    CropSuggestion,
    ImageMeta,
    ImprovementSuggestion,
    SuggestionType,
    SuggestionsResult,
    TechnicalScore,
)
from visionscore.pipeline.loader import LoadedImage

# Rule of thirds power points (normalized 0-1)
_POWER_POINTS = [
    (1 / 3, 1 / 3),
    (2 / 3, 1 / 3),
    (1 / 3, 2 / 3),
    (2 / 3, 2 / 3),
]

_STANDARD_ASPECTS = [
    ("16:9", 16 / 9),
    ("3:2", 3 / 2),
    ("4:3", 4 / 3),
    ("1:1", 1.0),
]


class SuggestionsAnalyzer(BaseAnalyzer):
    """Generate actionable photo improvement suggestions from prior analysis results."""

    def __init__(
        self,
        technical: TechnicalScore | None = None,
        composition: CompositionScore | None = None,
        ai_feedback: AIFeedback | None = None,
        output_dir: Path | None = None,
        ollama_host: str | None = None,
        ollama_model: str = "llava",
        thresholds: SuggestionThresholds | None = None,
    ) -> None:
        self._technical = technical
        self._composition = composition
        self._ai_feedback = ai_feedback
        self._output_dir = output_dir
        self._ollama_host = ollama_host
        self._ollama_model = ollama_model
        self._thresholds = thresholds or SuggestionThresholds()

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> SuggestionsResult:
        suggestions: list[ImprovementSuggestion] = []

        if self._technical:
            for fn in (self._suggest_exposure, self._suggest_contrast, self._suggest_sharpness):
                s = fn(self._technical, image)
                if s:
                    suggestions.append(s)
            color_s = self._suggest_color(image, self._technical)
            if color_s:
                suggestions.append(color_s)

        if self._composition:
            crop_s = self._suggest_crop(image, self._composition)
            if crop_s:
                suggestions.append(crop_s)
            horizon_s = self._suggest_horizon(self._composition)
            if horizon_s:
                suggestions.append(horizon_s)
            balance_s = self._suggest_composition_reframe(self._composition)
            if balance_s:
                suggestions.append(balance_s)

        suggestions.sort(key=lambda s: s.priority)
        suggestions = suggestions[: self._thresholds.max_suggestions]

        # Generate crop preview
        crop_preview_path: str | None = None
        crop_suggestions = [s for s in suggestions if s.type == SuggestionType.CROP]
        if crop_suggestions and crop_suggestions[0].crop_details:
            crop_preview_path = self._generate_crop_preview(image, crop_suggestions[0].crop_details)

        # Optionally polish with AI
        if self._ollama_host:
            suggestions = self._polish_with_ai(suggestions, image)

        summary = self._build_summary(suggestions)

        return SuggestionsResult(
            suggestions=suggestions,
            crop_preview_path=crop_preview_path,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Crop suggestion
    # ------------------------------------------------------------------

    def _suggest_crop(
        self, image: LoadedImage, comp: CompositionScore
    ) -> ImprovementSuggestion | None:
        trigger = self._thresholds.crop_trigger
        if comp.rule_of_thirds >= trigger and comp.subject_position >= (trigger - 10):
            return None

        centroid = comp.subject_centroid
        dims = comp.image_dimensions
        if not centroid or not dims:
            return None

        cx, cy = centroid
        img_w, img_h = dims

        # Find nearest power point
        nearest_pp = min(_POWER_POINTS, key=lambda pp: math.hypot(cx - pp[0], cy - pp[1]))
        target_px, target_py = nearest_pp

        # Try each standard aspect ratio; pick the one that gives largest crop area
        best_crop: CropSuggestion | None = None
        best_area = 0

        for aspect_name, aspect_ratio in _STANDARD_ASPECTS:
            crop = self._compute_crop_rect(
                img_w, img_h, cx, cy, target_px, target_py, aspect_ratio, aspect_name
            )
            if crop is None:
                continue
            area = crop.target_w * crop.target_h
            if area > best_area:
                best_area = area
                best_crop = crop

        if best_crop is None:
            return None

        # Ensure crop is at least 50% of original area
        if best_crop.target_w * best_crop.target_h < 0.5 * img_w * img_h:
            return None

        # Build instruction
        direction_x = "left" if best_crop.shift_x_pct < 0 else "right"
        direction_y = "up" if best_crop.shift_y_pct < 0 else "down"
        shift_desc = []
        if abs(best_crop.shift_x_pct) > 2:
            shift_desc.append(f"shifting {direction_x} {abs(best_crop.shift_x_pct):.0f}%")
        if abs(best_crop.shift_y_pct) > 2:
            shift_desc.append(f"shifting {direction_y} {abs(best_crop.shift_y_pct):.0f}%")

        # Determine which third the subject will be on
        third_x = "left" if target_px < 0.5 else "right"
        third_y = "upper" if target_py < 0.5 else "lower"

        shift_text = ", ".join(shift_desc) if shift_desc else "centering on subject"
        instruction = (
            f"Crop to {best_crop.aspect_ratio}, {shift_text} "
            f"to place subject on {third_x} {third_y} third"
        )

        priority = 1 if comp.rule_of_thirds < 40 else 2

        return ImprovementSuggestion(
            type=SuggestionType.CROP,
            instruction=instruction,
            priority=priority,
            parameters={
                "aspect_ratio": best_crop.aspect_ratio,
                "shift_x_pct": round(best_crop.shift_x_pct, 1),
                "shift_y_pct": round(best_crop.shift_y_pct, 1),
            },
            crop_details=best_crop,
        )

    def _compute_crop_rect(
        self,
        img_w: int,
        img_h: int,
        cx: float,
        cy: float,
        target_px: float,
        target_py: float,
        aspect_ratio: float,
        aspect_name: str,
    ) -> CropSuggestion | None:
        """Compute a crop rectangle that moves centroid (cx,cy) to target power point."""
        # Determine crop dimensions that fit within the image at this aspect ratio
        crop_w = img_w
        crop_h = int(crop_w / aspect_ratio)
        if crop_h > img_h:
            crop_h = img_h
            crop_w = int(crop_h * aspect_ratio)

        if crop_w < 1 or crop_h < 1:
            return None

        # The subject is at (cx * img_w, cy * img_h) in pixel coords.
        # We want it at (target_px * crop_w, target_py * crop_h) within the crop.
        subject_x = cx * img_w
        subject_y = cy * img_h

        # Crop origin so subject lands at the target position within crop
        crop_x = int(subject_x - target_px * crop_w)
        crop_y = int(subject_y - target_py * crop_h)

        # Clamp to image bounds
        crop_x = max(0, min(crop_x, img_w - crop_w))
        crop_y = max(0, min(crop_y, img_h - crop_h))

        # Compute shift percentages relative to a centered crop
        center_x = (img_w - crop_w) / 2
        center_y = (img_h - crop_h) / 2
        shift_x_pct = ((crop_x - center_x) / img_w) * 100 if img_w > 0 else 0.0
        shift_y_pct = ((crop_y - center_y) / img_h) * 100 if img_h > 0 else 0.0

        return CropSuggestion(
            aspect_ratio=aspect_name,
            shift_x_pct=round(shift_x_pct, 1),
            shift_y_pct=round(shift_y_pct, 1),
            target_x=crop_x,
            target_y=crop_y,
            target_w=crop_w,
            target_h=crop_h,
        )

    # ------------------------------------------------------------------
    # Exposure suggestion
    # ------------------------------------------------------------------

    def _suggest_exposure(
        self, tech: TechnicalScore, image: LoadedImage
    ) -> ImprovementSuggestion | None:
        if tech.exposure >= self._thresholds.exposure_trigger:
            return None

        # Determine direction from actual image luminance
        lab = cv2.cvtColor(image.resized, cv2.COLOR_BGR2LAB)
        mean_l = float(lab[:, :, 0].mean())
        midpoint = 128.0  # L channel midpoint

        if mean_l < midpoint:
            direction = "increase"
            sign = "+"
        else:
            direction = "decrease"
            sign = "-"

        # Map score to stop adjustment
        score = tech.exposure
        if score < 20:
            stops = 2.0
        elif score < 40:
            stops = 1.0
        else:
            stops = 0.5

        priority = 1 if score < 20 else (2 if score < 40 else 3)

        instruction = f"{direction.capitalize()} exposure by {sign}{stops} stops"

        return ImprovementSuggestion(
            type=SuggestionType.EXPOSURE,
            instruction=instruction,
            priority=priority,
            parameters={"stops": stops, "direction": direction},
        )

    # ------------------------------------------------------------------
    # Contrast suggestion
    # ------------------------------------------------------------------

    def _suggest_contrast(
        self, tech: TechnicalScore, image: LoadedImage
    ) -> ImprovementSuggestion | None:
        if tech.dynamic_range >= self._thresholds.contrast_trigger:
            return None

        utilization = round(tech.dynamic_range, 0)
        priority = 2 if tech.dynamic_range < 30 else 3

        instruction = (
            f"Increase contrast -- the image uses only ~{utilization:.0f}% "
            f"of the available tonal range"
        )

        return ImprovementSuggestion(
            type=SuggestionType.CONTRAST,
            instruction=instruction,
            priority=priority,
            parameters={"tonal_utilization_pct": utilization},
        )

    # ------------------------------------------------------------------
    # Sharpness suggestion
    # ------------------------------------------------------------------

    def _suggest_sharpness(
        self, tech: TechnicalScore, image: LoadedImage
    ) -> ImprovementSuggestion | None:
        if tech.sharpness >= self._thresholds.sharpness_trigger:
            return None

        score = tech.sharpness
        if score < 20:
            softness = "very soft"
            amount = "strong"
        elif score < 35:
            softness = "soft"
            amount = "moderate"
        else:
            softness = "slightly soft"
            amount = "subtle"

        priority = 1 if score < 20 else (2 if score < 35 else 3)

        instruction = f"Apply {amount} sharpening -- the image appears {softness}"

        return ImprovementSuggestion(
            type=SuggestionType.SHARPNESS,
            instruction=instruction,
            priority=priority,
            parameters={"sharpness_score": round(score, 1), "recommended_amount": amount},
        )

    # ------------------------------------------------------------------
    # Horizon suggestion
    # ------------------------------------------------------------------

    def _suggest_horizon(self, comp: CompositionScore) -> ImprovementSuggestion | None:
        if comp.horizon >= self._thresholds.horizon_trigger:
            return None
        if comp.horizon_angle is None:
            return None

        angle = comp.horizon_angle
        abs_angle = abs(angle)
        # Positive angle = tilted clockwise, need counterclockwise correction
        if angle > 0:
            direction = "counterclockwise"
        else:
            direction = "clockwise"

        priority = 2 if abs_angle > 5 else 3

        instruction = f"Straighten the horizon by rotating {abs_angle:.1f} degrees {direction}"

        return ImprovementSuggestion(
            type=SuggestionType.HORIZON,
            instruction=instruction,
            priority=priority,
            parameters={"rotate_degrees": round(abs_angle, 1), "direction": direction},
        )

    # ------------------------------------------------------------------
    # Color suggestion
    # ------------------------------------------------------------------

    def _suggest_color(
        self, image: LoadedImage, tech: TechnicalScore
    ) -> ImprovementSuggestion | None:
        lab = cv2.cvtColor(image.resized, cv2.COLOR_BGR2LAB)
        mean_a = float(lab[:, :, 1].mean())  # green-red axis
        mean_b = float(lab[:, :, 2].mean())  # blue-yellow axis

        # LAB A/B channels center at 128; deviations indicate color cast
        shifts: list[str] = []
        warmth = "neutral"

        if mean_a > 135:
            shifts.append("reduce magenta/red cast")
        elif mean_a < 120:
            shifts.append("reduce green cast")

        if mean_b > 135:
            shifts.append("reduce yellow cast")
            warmth = "cooler"
        elif mean_b < 120:
            shifts.append("reduce blue cast")
            warmth = "warmer"

        if not shifts:
            return None

        instruction = "Apply color correction: " + " and ".join(shifts)
        if warmth != "neutral":
            instruction += f" (try a slightly {warmth} grade)"

        return ImprovementSuggestion(
            type=SuggestionType.COLOR,
            instruction=instruction,
            priority=3,
            parameters={"color_shift": ", ".join(shifts), "warmth": warmth, "mean_a": round(mean_a, 1), "mean_b": round(mean_b, 1)},
        )

    # ------------------------------------------------------------------
    # Composition reframe suggestion
    # ------------------------------------------------------------------

    def _suggest_composition_reframe(self, comp: CompositionScore) -> ImprovementSuggestion | None:
        if comp.balance >= self._thresholds.balance_trigger:
            return None

        instruction = (
            "Consider reframing to balance visual weight -- "
            "the image has a significant imbalance in luminance or edge density"
        )

        return ImprovementSuggestion(
            type=SuggestionType.COMPOSITION,
            instruction=instruction,
            priority=4,
            parameters={"balance_score": round(comp.balance, 1)},
        )

    # ------------------------------------------------------------------
    # Crop preview generation
    # ------------------------------------------------------------------

    def _generate_crop_preview(self, image: LoadedImage, crop: CropSuggestion) -> str | None:
        try:
            x, y, w, h = crop.target_x, crop.target_y, crop.target_w, crop.target_h
            orig_h, orig_w = image.original.shape[:2]

            # Scale crop coords from resized to original dimensions
            res_h, res_w = image.resized.shape[:2]
            if res_w > 0 and res_h > 0:
                scale_x = orig_w / res_w
                scale_y = orig_h / res_h
                x = int(x * scale_x)
                y = int(y * scale_y)
                w = int(w * scale_x)
                h = int(h * scale_y)

            # Clamp
            x = max(0, min(x, orig_w - 1))
            y = max(0, min(y, orig_h - 1))
            w = min(w, orig_w - x)
            h = min(h, orig_h - y)

            if w < 1 or h < 1:
                return None

            cropped = image.original[y : y + h, x : x + w]

            output_dir = self._output_dir or image.path.parent
            stem = image.path.stem
            preview_path = output_dir / f"{stem}_crop_preview.jpg"
            cv2.imwrite(str(preview_path), cropped, [cv2.IMWRITE_JPEG_QUALITY, 90])

            return str(preview_path)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # AI polish layer
    # ------------------------------------------------------------------

    def _polish_with_ai(
        self, suggestions: list[ImprovementSuggestion], image: LoadedImage
    ) -> list[ImprovementSuggestion]:
        if not self._ollama_host or not suggestions:
            return suggestions

        try:
            import ollama

            client = ollama.Client(host=self._ollama_host)

            suggestion_data = [
                {"type": s.type.value, "instruction": s.instruction, "parameters": s.parameters}
                for s in suggestions
            ]

            prompt = (
                "You are an expert photography instructor. Below are structured improvement "
                "suggestions for the provided photograph. Rewrite each instruction into natural, "
                "photographer-friendly language. Keep them concise (under 20 words each).\n\n"
                f"Suggestions: {json.dumps(suggestion_data)}\n\n"
                "Respond with ONLY a JSON array of objects, each with 'type' and 'instruction' keys."
            )

            image_bytes = cv2.imencode(".jpg", image.resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not image_bytes[0]:
                return suggestions

            response = client.chat(
                model=self._ollama_model,
                messages=[
                    {"role": "user", "content": prompt, "images": [image_bytes[1].tobytes()]},
                ],
                format="json",
            )

            raw = response.message.content or ""
            polished = self._extract_json_array(raw)
            if polished and len(polished) == len(suggestions):
                for orig, pol in zip(suggestions, polished):
                    if isinstance(pol, dict) and "instruction" in pol:
                        orig.instruction = str(pol["instruction"])

        except Exception:
            pass  # Silent fallback to algorithmic instructions

        return suggestions

    @staticmethod
    def _extract_json_array(raw: str) -> list[dict[str, Any]] | None:
        # Direct parse
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "suggestions" in data:
                return data["suggestions"]
        except json.JSONDecodeError:
            pass

        # Strip markdown fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1))
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        # Bracket matching
        start = raw.find("[")
        if start != -1:
            depth = 0
            for i in range(start, len(raw)):
                if raw[i] == "[":
                    depth += 1
                elif raw[i] == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(raw[start : i + 1])
                            if isinstance(data, list):
                                return data
                        except json.JSONDecodeError:
                            pass
                        break

        return None

    # ------------------------------------------------------------------
    # Summary builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(suggestions: list[ImprovementSuggestion]) -> str:
        if not suggestions:
            return "No improvement suggestions -- the image looks great!"

        high_priority = [s for s in suggestions if s.priority <= 2]
        if high_priority:
            types = ", ".join(s.type.value for s in high_priority)
            return f"Focus on: {types} for the biggest improvement"

        types = ", ".join(s.type.value for s in suggestions[:3])
        return f"Minor tweaks suggested: {types}"
