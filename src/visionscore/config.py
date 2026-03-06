from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnalysisWeights(BaseModel):
    technical: float = 0.25
    aesthetic: float = 0.30
    composition: float = 0.25
    ai_feedback: float = 0.20


class Thresholds(BaseModel):
    blur_threshold: float = 100.0
    noise_threshold: float = 10.0
    exposure_low: int = 40
    exposure_high: int = 220


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llava"
    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_service_role_key: str | None = None
    model_dir: Path = Path.home() / ".visionscore" / "models"
    max_image_size: int = 1024
    output_format: str = "text"
    analysis_weights: AnalysisWeights = AnalysisWeights()
    thresholds: Thresholds = Thresholds()
