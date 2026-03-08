from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse

from visionscore import __version__
from visionscore.api.schemas import (
    AnalyzeResponse,
    BatchGroupsResponse,
    BatchSaveResponse,
    HealthResponse,
    ReportListResponse,
    SavedReportResponse,
)
from visionscore.api.supabase_client import (
    SupabaseClient,
    get_supabase_client,
)
from visionscore.pipeline.loader import SUPPORTED_EXTENSIONS

router = APIRouter()

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_supabase(request: Request) -> SupabaseClient | None:
    return get_supabase_client(request.app.state.settings)


def _require_supabase(
    db: SupabaseClient | None = Depends(_get_supabase),
) -> SupabaseClient:
    if db is None:
        raise HTTPException(503, "Supabase is not configured")
    return db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_extension(filename: str | None) -> str:
    """Return the lowercased file extension or raise 400."""
    if not filename:
        raise HTTPException(400, "Filename is required")
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported format '{suffix}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
    return suffix


def _save_image_locally(content: bytes, filename: str) -> str:
    """Save image to local uploads dir and return the API URL path."""
    suffix = Path(filename).suffix.lower() or ".jpg"
    name = f"{uuid4().hex}{suffix}"
    (UPLOADS_DIR / name).write_bytes(content)
    return f"/api/v1/uploads/{name}"


async def _read_upload(file: UploadFile) -> bytes:
    """Read upload with size limit."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(8192):
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f"File too large. Max: {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
        chunks.append(chunk)
    if total == 0:
        raise HTTPException(400, "Uploaded file is empty")
    return b"".join(chunks)


async def _run_analysis(
    content: bytes,
    suffix: str,
    request: Request,
    skip_ai: bool,
    weights: str | None,
) -> tuple:
    """Write content to temp file, run orchestrator, return (report, warnings)."""
    from visionscore.config import AnalysisWeights
    from visionscore.pipeline.orchestrator import AnalysisOrchestrator

    settings = request.app.state.settings

    if weights:
        parts = weights.split(":")
        if len(parts) != 4:
            raise HTTPException(400, "weights must be 4 colon-separated numbers (t:a:c:f)")
        try:
            raw = [float(p) for p in parts]
        except ValueError:
            raise HTTPException(400, "weights values must be numbers")
        total = sum(raw)
        if total <= 0:
            raise HTTPException(400, "weights must sum to a positive number")
        settings = settings.model_copy(
            update={
                "analysis_weights": AnalysisWeights(
                    technical=raw[0] / total,
                    aesthetic=raw[1] / total,
                    composition=raw[2] / total,
                    ai_feedback=raw[3] / total,
                )
            }
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        orchestrator = AnalysisOrchestrator(settings=settings, skip_ai=skip_ai)
        report = await asyncio.to_thread(orchestrator.run, tmp_path)
        return report, orchestrator.warnings
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
)
async def health(request: Request):
    """Return service status, version, and Supabase connectivity."""
    db = get_supabase_client(request.app.state.settings)
    return HealthResponse(
        version=__version__,
        supabase_connected=db is not None,
    )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    tags=["analysis"],
    summary="Analyze an uploaded image",
    responses={
        400: {"description": "Invalid file format or empty file"},
        413: {"description": "File too large (max 20MB)"},
    },
)
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    skip_ai: bool = Query(False, description="Skip AI feedback analysis"),
    weights: str | None = Query(
        None,
        description="Custom weights t:a:c:f (e.g. 25:30:25:20)",
        pattern=r"^\d+(\.\d+)?:\d+(\.\d+)?:\d+(\.\d+)?:\d+(\.\d+)?$",
    ),
):
    """Upload an image and receive a full quality analysis report."""
    suffix = _validate_extension(file.filename)
    content = await _read_upload(file)
    report, warnings = await _run_analysis(content, suffix, request, skip_ai, weights)
    return AnalyzeResponse(report=report, warnings=warnings)


@router.get(
    "/uploads/{filename}",
    tags=["system"],
    summary="Serve a locally stored image",
)
async def serve_upload(filename: str):
    """Serve an uploaded image from local storage."""
    # Prevent path traversal
    safe = Path(filename).name
    path = UPLOADS_DIR / safe
    if not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)


@router.post(
    "/analyze/save",
    response_model=SavedReportResponse,
    tags=["analysis"],
    summary="Analyze and save to Supabase",
    responses={
        400: {"description": "Invalid file format or empty file"},
        413: {"description": "File too large (max 20MB)"},
        503: {"description": "Supabase not configured"},
    },
)
async def analyze_and_save(
    request: Request,
    file: UploadFile = File(...),
    skip_ai: bool = Query(False, description="Skip AI feedback analysis"),
    db: SupabaseClient = Depends(_require_supabase),
):
    """Upload an image, run analysis, store image and report in Supabase."""
    suffix = _validate_extension(file.filename)
    content = await _read_upload(file)
    report, warnings = await _run_analysis(content, suffix, request, skip_ai, weights=None)

    image_url = await db.upload_image(content, file.filename or "image.jpg")
    if image_url is None:
        image_url = _save_image_locally(content, file.filename or "image.jpg")

    report_id = await db.save_report(report, image_url=image_url)

    if report_id is None:
        raise HTTPException(
            503,
            "Analysis succeeded but saving failed. "
            "Ensure the 'analysis_reports' table exists in Supabase (see sql/schema.sql).",
        )

    return SavedReportResponse(id=report_id, report=report, image_url=image_url, warnings=warnings)


@router.post(
    "/reports",
    response_model=SavedReportResponse,
    tags=["reports"],
    summary="Save an existing analysis report",
    responses={
        400: {"description": "Invalid file or report data"},
        503: {"description": "Supabase not configured"},
    },
)
async def save_report(
    request: Request,
    file: UploadFile = File(...),
    report_json: str = Form(...),
    db: SupabaseClient = Depends(_require_supabase),
):
    """Save an already-analyzed report with its image (no re-analysis)."""
    import json
    from visionscore.models import AnalysisReport

    try:
        report_data = json.loads(report_json)
        report = AnalysisReport(**report_data)
    except Exception:
        raise HTTPException(400, "Invalid report data")

    content = await _read_upload(file)

    image_url = await db.upload_image(content, file.filename or "image.jpg")
    if image_url is None:
        image_url = _save_image_locally(content, file.filename or "image.jpg")

    report_id = await db.save_report(report, image_url=image_url)

    if report_id is None:
        raise HTTPException(
            503,
            "Saving failed. Ensure the 'analysis_reports' table exists in Supabase.",
        )

    return SavedReportResponse(id=report_id, report=report, image_url=image_url)


@router.get(
    "/reports",
    response_model=ReportListResponse,
    tags=["reports"],
    summary="List analysis reports",
    responses={503: {"description": "Supabase not configured"}},
)
async def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    report_type: str | None = Query(None, description="Filter by 'single' or 'batch'"),
    db: SupabaseClient = Depends(_require_supabase),
):
    """List saved analysis reports with pagination."""
    reports, total = await db.list_reports(limit=limit, offset=offset, report_type=report_type)
    return ReportListResponse(reports=reports, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Batch routes (must be defined BEFORE /reports/{report_id} to avoid
# FastAPI matching "batch" or "batches" as a report_id parameter)
# ---------------------------------------------------------------------------


@router.post(
    "/reports/batch",
    response_model=BatchSaveResponse,
    tags=["reports"],
    summary="Save a batch of analyzed reports",
    responses={
        400: {"description": "Invalid report data"},
        503: {"description": "Supabase not configured"},
    },
)
async def save_batch(
    files: list[UploadFile] = File(...),
    reports_json: str = Form(...),
    db: SupabaseClient = Depends(_require_supabase),
):
    """Save multiple already-analyzed reports as a batch."""
    import json
    from visionscore.models import AnalysisReport

    try:
        reports_map = json.loads(reports_json)
    except Exception:
        raise HTTPException(400, "Invalid reports JSON")

    batch_id = str(uuid4())
    saved_count = 0

    for file in files:
        filename = file.filename or "image.jpg"
        report_data = reports_map.get(filename)
        if not report_data:
            continue

        try:
            report = AnalysisReport(**report_data)
        except Exception:
            continue

        content = await _read_upload(file)

        image_url = await db.upload_image(content, filename)
        if image_url is None:
            image_url = _save_image_locally(content, filename)

        report_id = await db.save_report(
            report, image_url=image_url, report_type="batch", batch_id=batch_id
        )
        if report_id:
            saved_count += 1

    if saved_count == 0:
        raise HTTPException(400, "No reports could be saved")

    return BatchSaveResponse(batch_id=batch_id, saved_count=saved_count)


@router.get(
    "/reports/batches",
    response_model=BatchGroupsResponse,
    tags=["reports"],
    summary="List batch groups",
    responses={503: {"description": "Supabase not configured"}},
)
async def list_batch_groups(
    db: SupabaseClient = Depends(_require_supabase),
):
    """List all batch groups with aggregated stats."""
    batches = await db.list_batch_groups()
    return BatchGroupsResponse(batches=batches)


@router.get(
    "/reports/batch/{batch_id}",
    tags=["reports"],
    summary="Get all reports in a batch",
    responses={
        404: {"description": "Batch not found"},
        503: {"description": "Supabase not configured"},
    },
)
async def get_batch(
    batch_id: str,
    db: SupabaseClient = Depends(_require_supabase),
):
    """Fetch all reports belonging to a batch."""
    reports = await db.get_batch_reports(batch_id)
    if not reports:
        raise HTTPException(404, "Batch not found")
    return {"batch_id": batch_id, "reports": reports}


@router.delete(
    "/reports/batch/{batch_id}",
    tags=["reports"],
    summary="Delete an entire batch",
    responses={
        404: {"description": "Batch not found"},
        503: {"description": "Supabase not configured"},
    },
)
async def delete_batch(
    batch_id: str,
    db: SupabaseClient = Depends(_require_supabase),
):
    """Delete all reports in a batch."""
    deleted = await db.delete_batch(batch_id)
    if not deleted:
        raise HTTPException(404, "Batch not found")
    return {"detail": "Batch deleted"}


# ---------------------------------------------------------------------------
# Single report routes (parameterized — must come after /reports/batch*)
# ---------------------------------------------------------------------------


@router.get(
    "/reports/{report_id}",
    tags=["reports"],
    summary="Get a single report",
    responses={
        404: {"description": "Report not found"},
        503: {"description": "Supabase not configured"},
    },
)
async def get_report(
    report_id: str,
    db: SupabaseClient = Depends(_require_supabase),
):
    """Fetch a single analysis report by ID."""
    report = await db.get_report(report_id)
    if report is None:
        raise HTTPException(404, "Report not found")
    return report


@router.delete(
    "/reports/{report_id}",
    tags=["reports"],
    summary="Delete a report",
    responses={
        404: {"description": "Report not found"},
        503: {"description": "Supabase not configured"},
    },
)
async def delete_report(
    report_id: str,
    db: SupabaseClient = Depends(_require_supabase),
):
    """Delete an analysis report by ID."""
    deleted = await db.delete_report(report_id)
    if not deleted:
        raise HTTPException(404, "Report not found")
    return {"detail": "Report deleted"}
