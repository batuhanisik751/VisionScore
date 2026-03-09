from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ImageMeta(BaseModel):
    path: str
    width: int = 0
    height: int = 0
    format: str = ""
    exif: dict[str, Any] = Field(default_factory=dict)


class TechnicalScore(BaseModel):
    sharpness: float = Field(ge=0, le=100)
    exposure: float = Field(ge=0, le=100)
    noise: float = Field(ge=0, le=100)
    dynamic_range: float = Field(ge=0, le=100)
    overall: float = Field(ge=0, le=100)


class AestheticScore(BaseModel):
    nima_score: float = Field(ge=0, le=100)
    std_dev: float = Field(ge=0, le=5.0, default=0.0)
    confidence: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=100)


class CompositionScore(BaseModel):
    rule_of_thirds: float = Field(ge=0, le=100)
    subject_position: float = Field(ge=0, le=100)
    horizon: float = Field(ge=0, le=100)
    balance: float = Field(ge=0, le=100)
    overall: float = Field(ge=0, le=100)
    # Overlay data (optional, for frontend visualization)
    subject_centroid: tuple[float, float] | None = None
    subject_bbox: tuple[int, int, int, int] | None = None
    horizon_angle: float | None = None
    image_dimensions: tuple[int, int] | None = None


class AIFeedback(BaseModel):
    description: str = ""
    genre: str = ""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    mood: str = ""
    score: float = Field(ge=0, le=100, default=0)
    reasoning: str = ""


class SuggestionType(str, Enum):
    CROP = "crop"
    EXPOSURE = "exposure"
    COLOR = "color"
    CONTRAST = "contrast"
    SHARPNESS = "sharpness"
    HORIZON = "horizon"
    COMPOSITION = "composition"


class CropSuggestion(BaseModel):
    """Structured crop recommendation with exact coordinates."""

    aspect_ratio: str = ""
    shift_x_pct: float = 0.0
    shift_y_pct: float = 0.0
    target_x: int = 0
    target_y: int = 0
    target_w: int = 0
    target_h: int = 0


class ImprovementSuggestion(BaseModel):
    """A single actionable photo edit suggestion."""

    type: SuggestionType
    instruction: str = ""
    priority: int = Field(ge=1, le=5, default=3)
    parameters: dict[str, Any] = Field(default_factory=dict)
    crop_details: CropSuggestion | None = None


class SuggestionsResult(BaseModel):
    """Output of the SuggestionsAnalyzer."""

    suggestions: list[ImprovementSuggestion] = Field(default_factory=list)
    crop_preview_path: str | None = None
    summary: str = ""


class Grade(str, Enum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class AnalysisReport(BaseModel):
    image_meta: ImageMeta
    technical: TechnicalScore | None = None
    aesthetic: AestheticScore | None = None
    composition: CompositionScore | None = None
    ai_feedback: AIFeedback | None = None
    suggestions: SuggestionsResult | None = None
    plugin_results: dict[str, Any] = Field(default_factory=dict)
    overall_score: float = Field(ge=0, le=100, default=0)
    grade: Grade = Grade.F
    timestamp: datetime = Field(default_factory=datetime.now)
    analysis_time_seconds: float = 0.0


class ScoreDiff(BaseModel):
    """Score difference between two analyses."""

    label: str
    score_a: float
    score_b: float
    diff: float  # b - a (positive = improved)


class ComparisonReport(BaseModel):
    """Result of comparing two image analyses."""

    report_a: AnalysisReport
    report_b: AnalysisReport
    overall_diff: float = 0.0
    category_diffs: list[ScoreDiff] = Field(default_factory=list)
    detail_diffs: list[ScoreDiff] = Field(default_factory=list)
    improved: list[str] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class BatchImageResult(BaseModel):
    """Result for a single image within a batch run."""

    report: AnalysisReport | None = None
    error: str | None = None
    filename: str = ""


class BatchResult(BaseModel):
    """Aggregate result of analyzing a directory of images."""

    directory: str = ""
    total_images: int = 0
    successful: int = 0
    failed: int = 0
    results: list[BatchImageResult] = Field(default_factory=list)
    average_score: float = 0.0
    best_image: str = ""
    best_score: float = 0.0
    worst_image: str = ""
    worst_score: float = 100.0
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    total_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)
