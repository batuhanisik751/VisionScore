"""API key authentication for the VisionScore API."""

from __future__ import annotations

import hashlib
import secrets

from fastapi import Depends, HTTPException, Request

from visionscore.api.supabase_client import SupabaseClient


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns ``(raw_key, key_hash)``."""
    raw = f"vs_{secrets.token_hex(16)}"
    return raw, hash_api_key(raw)


def hash_api_key(raw: str) -> str:
    """Return the SHA-256 hex digest of *raw*."""
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_settings(request: Request):
    return request.app.state.settings


async def get_optional_api_key(request: Request) -> str | None:
    """Extract the ``X-API-Key`` header value, or ``None`` if absent."""
    return request.headers.get("x-api-key")


async def validate_api_key(
    request: Request,
    db: SupabaseClient | None = None,
) -> dict | None:
    """Validate an API key if auth is enabled.

    Returns the key row dict when a valid key is provided,
    ``None`` when auth is disabled and no key is sent,
    or raises 401/403 when auth is required but the key is missing/invalid.
    """
    settings = _get_settings(request)
    raw_key = request.headers.get("x-api-key")

    if not raw_key:
        if settings.api_auth_enabled:
            raise HTTPException(401, "API key required")
        return None

    if db is None:
        raise HTTPException(503, "Database not available for key validation")

    key_hash = hash_api_key(raw_key)
    key_row = await db.get_api_key_by_hash(key_hash)

    if key_row is None:
        raise HTTPException(403, "Invalid API key")

    # Fire-and-forget last_used_at update
    import asyncio
    asyncio.create_task(db.update_api_key_last_used(key_row["id"]))

    return key_row


def require_admin_key(request: Request) -> None:
    """Verify the ``X-Admin-Key`` header matches the configured admin key.

    Raises 401 if missing, 403 if wrong, or passes silently if no admin key is configured.
    """
    settings = _get_settings(request)
    if not settings.api_admin_key:
        # No admin key configured — allow access (development mode)
        return

    admin_key = request.headers.get("x-admin-key")
    if not admin_key:
        raise HTTPException(401, "Admin key required")
    if not secrets.compare_digest(admin_key, settings.api_admin_key):
        raise HTTPException(403, "Invalid admin key")
