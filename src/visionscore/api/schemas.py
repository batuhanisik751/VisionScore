from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from visionscore.models import AnalysisReport


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    supabase_connected: bool


class AnalyzeResponse(BaseModel):
    report: AnalysisReport
    warnings: list[str] = Field(default_factory=list)


class SavedReportResponse(BaseModel):
    id: str
    report: AnalysisReport
    image_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ReportListResponse(BaseModel):
    reports: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class BatchSaveResponse(BaseModel):
    batch_id: str
    saved_count: int
    errors_saved: int = 0


class BatchGroupsResponse(BaseModel):
    batches: list[dict[str, Any]]


class PluginResponse(BaseModel):
    name: str
    display_name: str
    version: str
    description: str
    score_weight: float
    score_field: str
    source: str = "unknown"


class PluginListResponse(BaseModel):
    plugins: list[PluginResponse]
    bundled_enabled: bool


class TrainingStatusResponse(BaseModel):
    running: bool
    progress: dict[str, Any] = Field(default_factory=dict)
