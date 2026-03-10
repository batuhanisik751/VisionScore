from __future__ import annotations

import math
import time
from pathlib import Path

import cv2
import numpy as np

from visionscore.models import (
    AppliedEdit,
    AutoEditResult,
    CropSuggestion,
    ImprovementSuggestion,
    SuggestionType,
)

# Fixed order: geometry first, then pixel adjustments, sharpness last.
_EDIT_ORDER: list[SuggestionType] = [
    SuggestionType.HORIZON,
    SuggestionType.CROP,
    SuggestionType.EXPOSURE,
    SuggestionType.CONTRAST,
    SuggestionType.COLOR,
    SuggestionType.SHARPNESS,
]

# Gamma values keyed by stops: (increase_gamma, decrease_gamma)
_GAMMA_MAP: dict[float, tuple[float, float]] = {
    0.5: (0.85, 1.18),
    1.0: (0.71, 1.41),
    2.0: (0.5, 2.0),
}


# ---------------------------------------------------------------------------
# Individual edit functions
# ---------------------------------------------------------------------------


def apply_horizon(image: np.ndarray, rotate_degrees: float, direction: str) -> np.ndarray:
    """Rotate image to level the horizon and auto-crop to remove black borders."""
    angle = rotate_degrees if direction == "counterclockwise" else -rotate_degrees
    if abs(angle) < 0.1:
        return image

    h, w = image.shape[:2]
    center = (w / 2, h / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR)

    # Auto-crop: largest inscribed axis-aligned rectangle after rotation.
    theta = math.radians(abs(angle))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    if w <= 0 or h <= 0 or cos_t == 0:
        return rotated

    # Inscribed rectangle dimensions.
    new_w = int(w * cos_t - h * sin_t)
    new_h = int(h * cos_t - w * sin_t)

    if new_w <= 0 or new_h <= 0:
        return rotated

    x_start = (w - new_w) // 2
    y_start = (h - new_h) // 2
    return rotated[y_start : y_start + new_h, x_start : x_start + new_w]


def apply_crop(
    image: np.ndarray,
    crop: CropSuggestion,
    scale_x: float,
    scale_y: float,
) -> np.ndarray:
    """Crop using coordinates scaled from resized-image space to original."""
    h, w = image.shape[:2]
    x = max(0, int(crop.target_x * scale_x))
    y = max(0, int(crop.target_y * scale_y))
    cw = max(1, int(crop.target_w * scale_x))
    ch = max(1, int(crop.target_h * scale_y))

    # Clamp to image bounds.
    x = min(x, w - 1)
    y = min(y, h - 1)
    cw = min(cw, w - x)
    ch = min(ch, h - y)

    return image[y : y + ch, x : x + cw]


def apply_exposure(image: np.ndarray, stops: float, direction: str) -> np.ndarray:
    """Adjust exposure via gamma correction."""
    inc, dec = _GAMMA_MAP.get(stops, _GAMMA_MAP[1.0])
    gamma = inc if direction == "increase" else dec

    table = np.array(
        [np.clip(((i / 255.0) ** gamma) * 255.0, 0, 255) for i in range(256)],
        dtype=np.uint8,
    )
    return cv2.LUT(image, table)


def apply_contrast(image: np.ndarray, black_point: int, white_point: int) -> np.ndarray:
    """Apply levels stretch between black_point and white_point."""
    if white_point <= black_point:
        return image

    span = white_point - black_point
    table = np.array(
        [np.clip(int((i - black_point) * 255.0 / span), 0, 255) for i in range(256)],
        dtype=np.uint8,
    )
    return cv2.LUT(image, table)


def apply_color(image: np.ndarray, mean_a: float, mean_b: float) -> np.ndarray:
    """Shift LAB A/B channels toward neutral (128) with 70% correction."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)

    delta_a = 128.0 - mean_a
    delta_b = 128.0 - mean_b

    # Skip if already near neutral.
    if abs(delta_a) < 2.0 and abs(delta_b) < 2.0:
        return image

    lab[:, :, 1] += 0.7 * delta_a
    lab[:, :, 2] += 0.7 * delta_b
    lab = np.clip(lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def apply_sharpness(
    image: np.ndarray,
    usm_amount_pct: int,
    usm_radius_px: float,
    usm_threshold: int,
) -> np.ndarray:
    """Apply Unsharp Mask sharpening."""
    ksize = int(usm_radius_px * 6) | 1
    if ksize < 3:
        ksize = 3

    blurred = cv2.GaussianBlur(image, (ksize, ksize), usm_radius_px)
    diff = image.astype(np.int16) - blurred.astype(np.int16)

    if usm_threshold > 0:
        mask = (np.abs(diff) > usm_threshold).astype(np.int16)
        diff = diff * mask

    amount = usm_amount_pct / 100.0
    sharpened = image.astype(np.int16) + (diff * amount).astype(np.int16)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

def _apply_suggestion(
    image: np.ndarray,
    suggestion: ImprovementSuggestion,
    scale_x: float,
    scale_y: float,
) -> np.ndarray:
    """Dispatch a single suggestion to the correct edit function."""
    p = suggestion.parameters
    t = suggestion.type

    if t == SuggestionType.HORIZON:
        return apply_horizon(image, p.get("rotate_degrees", 0.0), p.get("direction", "clockwise"))
    if t == SuggestionType.CROP and suggestion.crop_details:
        return apply_crop(image, suggestion.crop_details, scale_x, scale_y)
    if t == SuggestionType.EXPOSURE:
        return apply_exposure(image, p.get("stops", 1.0), p.get("direction", "increase"))
    if t == SuggestionType.CONTRAST:
        return apply_contrast(image, int(p.get("black_point", 0)), int(p.get("white_point", 255)))
    if t == SuggestionType.COLOR:
        return apply_color(image, p.get("mean_a", 128.0), p.get("mean_b", 128.0))
    if t == SuggestionType.SHARPNESS:
        return apply_sharpness(
            image,
            int(p.get("usm_amount_pct", 100)),
            float(p.get("usm_radius_px", 1.0)),
            int(p.get("usm_threshold", 2)),
        )
    return image


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def auto_edit(
    image: np.ndarray,
    suggestions: list[ImprovementSuggestion],
    scale_x: float = 1.0,
    scale_y: float = 1.0,
) -> tuple[np.ndarray, list[AppliedEdit], list[str]]:
    """Apply suggestions in the correct order.

    Returns (edited_image, applied_edits, skipped_messages).
    """
    lookup: dict[SuggestionType, ImprovementSuggestion] = {}
    for s in suggestions:
        if s.type not in lookup:
            lookup[s.type] = s

    applied: list[AppliedEdit] = []
    skipped: list[str] = []
    result = image.copy()

    # Apply in fixed order.
    for edit_type in _EDIT_ORDER:
        suggestion = lookup.pop(edit_type, None)
        if suggestion is None:
            continue
        result = _apply_suggestion(result, suggestion, scale_x, scale_y)
        applied.append(
            AppliedEdit(
                type=suggestion.type,
                instruction=suggestion.instruction,
                parameters=suggestion.parameters,
            )
        )

    # Any remaining types are non-applicable (e.g. COMPOSITION).
    for remaining_type, suggestion in lookup.items():
        skipped.append(f"{remaining_type.value}: advisory only, not auto-applicable")

    return result, applied, skipped


def run_auto_edit(
    image_path: Path,
    output_path: Path | None = None,
    skip_ai: bool = True,
) -> AutoEditResult:
    """High-level entry point: load image, run analysis, apply edits, save."""
    from visionscore.pipeline.loader import load_image
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    start = time.perf_counter()

    loaded = load_image(image_path)
    orchestrator = AnalysisOrchestrator(skip_ai=skip_ai)
    report = orchestrator.run(image_path)

    suggestions = report.suggestions.suggestions if report.suggestions else []
    if not suggestions:
        return AutoEditResult(
            original_path=str(image_path),
            edited_path="",
            applied_edits=[],
            skipped=[],
            edit_time_seconds=round(time.perf_counter() - start, 3),
        )

    # Scale factors: resized → original.
    resized_h, resized_w = loaded.resized.shape[:2]
    scale_x = loaded.width / resized_w if resized_w > 0 else 1.0
    scale_y = loaded.height / resized_h if resized_h > 0 else 1.0

    edited, applied, skipped = auto_edit(loaded.original, suggestions, scale_x, scale_y)

    # Default output path: {stem}_autofix{ext}
    if output_path is None:
        p = Path(image_path)
        output_path = p.parent / f"{p.stem}_autofix{p.suffix}"

    cv2.imwrite(str(output_path), edited)

    return AutoEditResult(
        original_path=str(image_path),
        edited_path=str(output_path),
        applied_edits=applied,
        skipped=skipped,
        edit_time_seconds=round(time.perf_counter() - start, 3),
    )
