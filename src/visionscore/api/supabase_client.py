from __future__ import annotations

import asyncio
from uuid import uuid4

from visionscore.config import Settings
from visionscore.models import AnalysisReport


class SupabaseClient:
    """Wrapper around the Supabase Python SDK for storage and database operations."""

    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client

        self._client = create_client(url, key)

    async def upload_image(self, file_bytes: bytes, filename: str) -> str:
        """Upload image to Supabase Storage and return the storage path."""
        path = f"uploads/{uuid4().hex}_{filename}"

        def _upload() -> str:
            self._client.storage.from_("images").upload(path, file_bytes)
            return self._client.storage.from_("images").get_public_url(path)

        return await asyncio.to_thread(_upload)

    async def save_report(
        self, report: AnalysisReport, image_url: str | None = None
    ) -> str:
        """Insert analysis report into the database and return the row ID."""
        data = report.model_dump(mode="json")
        row = {
            "image_path": report.image_meta.path,
            "image_url": image_url,
            "image_width": report.image_meta.width,
            "image_height": report.image_meta.height,
            "image_format": report.image_meta.format,
            "technical": data.get("technical"),
            "aesthetic": data.get("aesthetic"),
            "composition": data.get("composition"),
            "ai_feedback": data.get("ai_feedback"),
            "overall_score": report.overall_score,
            "grade": report.grade.value,
            "analysis_time_seconds": report.analysis_time_seconds,
            "full_report": data,
        }

        def _insert() -> str:
            result = (
                self._client.table("analysis_reports").insert(row).execute()
            )
            return result.data[0]["id"]

        return await asyncio.to_thread(_insert)

    async def get_report(self, report_id: str) -> dict | None:
        """Fetch a single report by ID."""

        def _select() -> dict | None:
            result = (
                self._client.table("analysis_reports")
                .select("*")
                .eq("id", report_id)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_select)

    async def list_reports(
        self, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict], int]:
        """List reports with pagination. Returns (rows, total_count)."""

        def _list() -> tuple[list[dict], int]:
            result = (
                self._client.table("analysis_reports")
                .select("*", count="exact")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data, result.count or 0

        return await asyncio.to_thread(_list)

    async def delete_report(self, report_id: str) -> bool:
        """Delete a report by ID. Returns True if a row was deleted."""

        def _delete() -> bool:
            result = (
                self._client.table("analysis_reports")
                .delete()
                .eq("id", report_id)
                .execute()
            )
            return len(result.data) > 0

        return await asyncio.to_thread(_delete)


_client: SupabaseClient | None = None


def get_supabase_client(
    settings: Settings | None = None,
) -> SupabaseClient | None:
    """Return a SupabaseClient if configured, None otherwise."""
    global _client
    if _client is not None:
        return _client
    s = settings or Settings()
    if not s.supabase_url or not s.supabase_key:
        return None
    _client = SupabaseClient(url=s.supabase_url, key=s.supabase_key)
    return _client


def reset_supabase_client() -> None:
    """Reset the cached client (used in tests)."""
    global _client
    _client = None
