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
    overall_score: float = Field(ge=0, le=100, default=0)
    grade: Grade = Grade.F
    timestamp: datetime = Field(default_factory=datetime.now)
    analysis_time_seconds: float = 0.0


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
