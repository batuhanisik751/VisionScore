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
