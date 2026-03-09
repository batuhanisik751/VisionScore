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


class LeaderboardEntry(BaseModel):
    id: str
    image_url: str | None = None
    overall_score: float
    grade: str
    created_at: str
    filename: str = ""
    genre: str | None = None


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    total: int
    potd: LeaderboardEntry | None = None
    average_score: float = 0.0
    grade_distribution: dict[str, int] = Field(default_factory=dict)


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


# ---- Mobile-Friendly API (Phase 9.8) ----


class ApiKeyCreateRequest(BaseModel):
    name: str
    rate_limit_per_minute: int = 60


class ApiKeyCreateResponse(BaseModel):
    id: str
    key: str
    name: str
    rate_limit_per_minute: int


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    rate_limit_per_minute: int
    created_at: str
    last_used_at: str | None = None


class ApiKeyListResponse(BaseModel):
    keys: list[ApiKeyInfo]


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = Field(
        default_factory=lambda: ["analysis.completed", "batch.completed"]
    )
    secret: str | None = None


class WebhookCreateResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool = True


class WebhookInfo(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str
    last_triggered_at: str | None = None
    failure_count: int = 0


class WebhookListResponse(BaseModel):
    webhooks: list[WebhookInfo]


# ---- SSE Upload (Phase 9.2 real-time progress) ----


class UploadResponse(BaseModel):
    task_id: str
