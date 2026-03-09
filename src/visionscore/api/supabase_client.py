from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from visionscore.config import Settings
from visionscore.models import AnalysisReport

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Wrapper around the Supabase Python SDK for storage and database operations."""

    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client

        self._client = create_client(url, key)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Check that the 'images' storage bucket exists, attempt to create if not."""
        try:
            buckets = self._client.storage.list_buckets()
            if any(b.name == "images" for b in buckets):
                return
            self._client.storage.create_bucket("images", options={"public": True})
        except Exception as e:
            logger.warning(
                "Could not verify/create 'images' bucket: %s. "
                "Create it manually in the Supabase dashboard.", e
            )

    async def upload_image(self, file_bytes: bytes, filename: str) -> str | None:
        """Upload image to Supabase Storage and return the public URL, or None on failure."""
        path = f"uploads/{uuid4().hex}_{filename}"

        def _upload() -> str | None:
            try:
                self._client.storage.from_("images").upload(path, file_bytes)
                return self._client.storage.from_("images").get_public_url(path)
            except Exception as e:
                logger.warning("Image upload failed: %s", e)
                return None

        return await asyncio.to_thread(_upload)

    async def save_report(
        self,
        report: AnalysisReport,
        image_url: str | None = None,
        report_type: str = "single",
        batch_id: str | None = None,
    ) -> str | None:
        """Insert analysis report into the database and return the row ID, or None on failure."""
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
            "report_type": report_type,
            "batch_id": batch_id,
        }

        def _insert() -> str | None:
            try:
                result = self._client.table("analysis_reports").insert(row).execute()
                return result.data[0]["id"]
            except Exception as e:
                logger.warning("Failed to save report: %s", e)
                # Retry without batch columns in case migration hasn't been applied
                fallback_row = {
                    k: v for k, v in row.items() if k not in ("report_type", "batch_id")
                }
                try:
                    result = (
                        self._client.table("analysis_reports")
                        .insert(fallback_row)
                        .execute()
                    )
                    logger.info("Saved report without batch columns (migration pending)")
                    return result.data[0]["id"]
                except Exception as e2:
                    logger.warning("Fallback save also failed: %s", e2)
                    return None

        return await asyncio.to_thread(_insert)

    async def get_report(self, report_id: str) -> dict | None:
        """Fetch a single report by ID."""

        def _select() -> dict | None:
            result = (
                self._client.table("analysis_reports").select("*").eq("id", report_id).execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_select)

    async def list_reports(
        self, limit: int = 20, offset: int = 0, report_type: str | None = None
    ) -> tuple[list[dict], int]:
        """List reports with pagination and optional type filter. Returns (rows, total_count)."""

        def _list() -> tuple[list[dict], int]:
            query = (
                self._client.table("analysis_reports")
                .select("*", count="exact")
            )
            if report_type:
                try:
                    result = (
                        query.eq("report_type", report_type)
                        .order("created_at", desc=True)
                        .range(offset, offset + limit - 1)
                        .execute()
                    )
                    return result.data, result.count or 0
                except Exception:
                    # report_type column may not exist yet — fall back to unfiltered
                    query = (
                        self._client.table("analysis_reports")
                        .select("*", count="exact")
                    )
            result = (
                query.order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return result.data, result.count or 0

        return await asyncio.to_thread(_list)

    async def get_batch_reports(self, batch_id: str) -> list[dict]:
        """Fetch all reports belonging to a batch."""

        def _select() -> list[dict]:
            try:
                result = (
                    self._client.table("analysis_reports")
                    .select("*")
                    .eq("batch_id", batch_id)
                    .order("created_at", desc=True)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Failed to fetch batch reports: %s", e)
                return []

        return await asyncio.to_thread(_select)

    async def list_batch_groups(self) -> list[dict]:
        """List batch groups with aggregated stats."""

        def _list() -> list[dict]:
            try:
                result = (
                    self._client.table("analysis_reports")
                    .select("*")
                    .eq("report_type", "batch")
                    .order("created_at", desc=True)
                    .execute()
                )
            except Exception as e:
                logger.warning("Failed to list batch groups: %s", e)
                return []

            groups: dict[str, list[dict]] = {}
            for row in result.data:
                bid = row.get("batch_id")
                if bid:
                    groups.setdefault(bid, []).append(row)

            batch_list = []
            for bid, rows in groups.items():
                ok_rows = [
                    r for r in rows
                    if not (r.get("full_report") or {}).get("error")
                ]
                error_count = len(rows) - len(ok_rows)
                scores = [r["overall_score"] for r in ok_rows]
                best_row = max(ok_rows, key=lambda r: r["overall_score"]) if ok_rows else None
                batch_list.append({
                    "batch_id": bid,
                    "created_at": rows[0]["created_at"],
                    "count": len(ok_rows),
                    "errors": error_count,
                    "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
                    "best_score": best_row["overall_score"] if best_row else 0,
                    "best_grade": best_row["grade"] if best_row else "F",
                    "image_urls": [r.get("image_url") for r in ok_rows[:4] if r.get("image_url")],
                })
            batch_list.sort(key=lambda b: b["created_at"], reverse=True)
            return batch_list

        return await asyncio.to_thread(_list)

    async def save_batch_errors(
        self,
        errors: dict[str, str],
        batch_id: str,
    ) -> int:
        """Save error placeholder records for failed batch images. Returns count saved."""

        def _insert() -> int:
            saved = 0
            for filename, error_msg in errors.items():
                row = {
                    "image_path": filename,
                    "overall_score": 0,
                    "grade": "F",
                    "full_report": {
                        "error": True,
                        "error_message": error_msg,
                        "image_meta": {
                            "path": filename,
                            "width": 0,
                            "height": 0,
                            "format": "",
                            "exif": {},
                        },
                        "overall_score": 0,
                        "grade": "F",
                        "timestamp": None,
                        "analysis_time_seconds": 0,
                    },
                    "report_type": "batch",
                    "batch_id": batch_id,
                }
                try:
                    self._client.table("analysis_reports").insert(row).execute()
                    saved += 1
                except Exception as e:
                    logger.warning("Failed to save batch error for %s: %s", filename, e)
            return saved

        return await asyncio.to_thread(_insert)

    async def get_leaderboard(
        self,
        limit: int = 50,
        offset: int = 0,
        min_score: float | None = None,
        max_score: float | None = None,
        grade: str | None = None,
        sort_by: str = "overall_score",
        sort_order: str = "desc",
        include_batch: bool = False,
    ) -> tuple[list[dict], int]:
        """Fetch ranked reports for the leaderboard. Returns (rows, total_count)."""

        def _query() -> tuple[list[dict], int]:
            q = self._client.table("analysis_reports").select("*", count="exact")

            if not include_batch:
                try:
                    q = q.neq("report_type", "batch")
                except Exception:
                    pass  # column may not exist

            if min_score is not None:
                q = q.gte("overall_score", min_score)
            if max_score is not None:
                q = q.lte("overall_score", max_score)
            if grade:
                q = q.eq("grade", grade)

            # Filter out error placeholder rows
            q = q.gt("overall_score", 0)

            col = "overall_score" if sort_by == "overall_score" else "created_at"
            desc = sort_order == "desc"

            try:
                result = (
                    q.order(col, desc=desc)
                    .range(offset, offset + limit - 1)
                    .execute()
                )
                return result.data, result.count or 0
            except Exception as e:
                logger.warning("Leaderboard query failed: %s", e)
                return [], 0

        return await asyncio.to_thread(_query)

    async def delete_batch(self, batch_id: str) -> bool:
        """Delete all reports in a batch. Returns True if any rows were deleted."""

        def _delete() -> bool:
            try:
                result = (
                    self._client.table("analysis_reports")
                    .delete()
                    .eq("batch_id", batch_id)
                    .execute()
                )
                return len(result.data) > 0
            except Exception as e:
                logger.warning("Failed to delete batch: %s", e)
                return False

        return await asyncio.to_thread(_delete)

    async def delete_report(self, report_id: str) -> bool:
        """Delete a report by ID. Returns True if a row was deleted."""

        def _delete() -> bool:
            result = self._client.table("analysis_reports").delete().eq("id", report_id).execute()
            return len(result.data) > 0

        return await asyncio.to_thread(_delete)

    # ---- API Key methods ----

    async def create_api_key(
        self, name: str, key_hash: str, key_prefix: str, rate_limit: int
    ) -> str | None:
        """Insert a new API key row and return its ID."""

        def _insert() -> str | None:
            try:
                result = (
                    self._client.table("api_keys")
                    .insert({
                        "name": name,
                        "key_hash": key_hash,
                        "key_prefix": key_prefix,
                        "rate_limit_per_minute": rate_limit,
                    })
                    .execute()
                )
                return result.data[0]["id"]
            except Exception as e:
                logger.warning("Failed to create API key: %s", e)
                return None

        return await asyncio.to_thread(_insert)

    async def get_api_key_by_hash(self, key_hash: str) -> dict | None:
        """Look up an active API key by its hash."""

        def _select() -> dict | None:
            result = (
                self._client.table("api_keys")
                .select("*")
                .eq("key_hash", key_hash)
                .eq("is_active", True)
                .execute()
            )
            return result.data[0] if result.data else None

        return await asyncio.to_thread(_select)

    async def list_api_keys(self) -> list[dict]:
        """List all API keys (active and inactive)."""

        def _list() -> list[dict]:
            result = (
                self._client.table("api_keys")
                .select("id,name,key_prefix,is_active,rate_limit_per_minute,created_at,last_used_at")
                .order("created_at", desc=True)
                .execute()
            )
            return result.data

        return await asyncio.to_thread(_list)

    async def deactivate_api_key(self, key_id: str) -> bool:
        """Soft-delete an API key by setting is_active=False."""

        def _update() -> bool:
            result = (
                self._client.table("api_keys")
                .update({"is_active": False})
                .eq("id", key_id)
                .execute()
            )
            return len(result.data) > 0

        return await asyncio.to_thread(_update)

    async def update_api_key_last_used(self, key_id: str) -> None:
        """Touch the last_used_at timestamp for an API key."""

        def _update() -> None:
            try:
                self._client.table("api_keys").update(
                    {"last_used_at": "now()"}
                ).eq("id", key_id).execute()
            except Exception as e:
                logger.debug("Failed to update last_used_at: %s", e)

        await asyncio.to_thread(_update)

    # ---- Webhook methods ----

    async def create_webhook(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
        api_key_id: str | None = None,
    ) -> str | None:
        """Register a new webhook and return its ID."""

        def _insert() -> str | None:
            try:
                row: dict = {"url": url, "events": events}
                if secret:
                    row["secret"] = secret
                if api_key_id:
                    row["api_key_id"] = api_key_id
                result = self._client.table("webhooks").insert(row).execute()
                return result.data[0]["id"]
            except Exception as e:
                logger.warning("Failed to create webhook: %s", e)
                return None

        return await asyncio.to_thread(_insert)

    async def list_webhooks(self) -> list[dict]:
        """List all webhooks."""

        def _list() -> list[dict]:
            result = (
                self._client.table("webhooks")
                .select("id,url,events,is_active,created_at,last_triggered_at,failure_count")
                .order("created_at", desc=True)
                .execute()
            )
            return result.data

        return await asyncio.to_thread(_list)

    async def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook by ID."""

        def _delete() -> bool:
            result = (
                self._client.table("webhooks").delete().eq("id", webhook_id).execute()
            )
            return len(result.data) > 0

        return await asyncio.to_thread(_delete)

    async def get_active_webhooks_for_event(self, event: str) -> list[dict]:
        """Fetch all active webhooks that subscribe to the given event."""

        def _select() -> list[dict]:
            try:
                result = (
                    self._client.table("webhooks")
                    .select("*")
                    .eq("is_active", True)
                    .contains("events", [event])
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Failed to fetch webhooks for event %s: %s", event, e)
                return []

        return await asyncio.to_thread(_select)

    async def record_webhook_delivery(
        self,
        webhook_id: str,
        event: str,
        payload: dict,
        status_code: int | None,
        response_body: str | None,
        success: bool,
        attempt: int = 1,
        next_retry_at: str | None = None,
    ) -> None:
        """Log a webhook delivery attempt."""

        def _insert() -> None:
            row: dict = {
                "webhook_id": webhook_id,
                "event": event,
                "payload": payload,
                "status_code": status_code,
                "response_body": (response_body or "")[:2000],
                "success": success,
                "attempt": attempt,
            }
            if next_retry_at:
                row["next_retry_at"] = next_retry_at
            try:
                self._client.table("webhook_deliveries").insert(row).execute()
            except Exception as e:
                logger.warning("Failed to record webhook delivery: %s", e)

            # Update webhook metadata
            try:
                update: dict = {"last_triggered_at": "now()"}
                if success:
                    update["failure_count"] = 0
                else:
                    # Increment failure count
                    wh = (
                        self._client.table("webhooks")
                        .select("failure_count")
                        .eq("id", webhook_id)
                        .execute()
                    )
                    count = (wh.data[0]["failure_count"] if wh.data else 0) + 1
                    update["failure_count"] = count
                    if count >= 10:
                        update["is_active"] = False
                self._client.table("webhooks").update(update).eq("id", webhook_id).execute()
            except Exception as e:
                logger.debug("Failed to update webhook metadata: %s", e)

        await asyncio.to_thread(_insert)

    async def get_failed_deliveries_for_retry(self) -> list[dict]:
        """Fetch failed deliveries that are due for retry."""

        def _select() -> list[dict]:
            try:
                from datetime import datetime, timezone

                now = datetime.now(timezone.utc).isoformat()
                result = (
                    self._client.table("webhook_deliveries")
                    .select("*")
                    .eq("success", False)
                    .lt("next_retry_at", now)
                    .lt("attempt", 4)
                    .order("next_retry_at")
                    .limit(50)
                    .execute()
                )
                return result.data
            except Exception as e:
                logger.warning("Failed to fetch deliveries for retry: %s", e)
                return []

        return await asyncio.to_thread(_select)


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
