from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, field_validator
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


class SuggestionThresholds(BaseModel):
    crop_trigger: float = 60.0
    exposure_trigger: float = 60.0
    contrast_trigger: float = 50.0
    sharpness_trigger: float = 50.0
    horizon_trigger: float = 70.0
    balance_trigger: float = 40.0
    max_suggestions: int = 5


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
    max_upload_mb: int = 20
    output_format: str = "text"
    device: str = "auto"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    custom_model_path: Path | None = None
    plugin_dir: Path = Path.home() / ".visionscore" / "plugins"
    enable_bundled_plugins: bool = False
    analysis_weights: AnalysisWeights = AnalysisWeights()
    thresholds: Thresholds = Thresholds()
    suggestion_thresholds: SuggestionThresholds = SuggestionThresholds()

    # Mobile-friendly API (Phase 9.8)
    api_auth_enabled: bool = False
    api_admin_key: str | None = None
    rate_limit_enabled: bool = True
    rate_limit_default_rpm: int = 60
    thumbnail_max_width: int = 400
    thumbnail_quality: int = 75

    @field_validator("model_dir", "plugin_dir", mode="before")
    @classmethod
    def _expand_path(cls, v: object) -> object:
        if isinstance(v, str):
            return Path(v).expanduser()
        if isinstance(v, Path):
            return v.expanduser()
        return v

    @field_validator("custom_model_path", mode="before")
    @classmethod
    def _expand_optional_path(cls, v: object) -> object:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        if isinstance(v, str):
            return Path(v).expanduser()
        if isinstance(v, Path):
            return v.expanduser()
        return v
