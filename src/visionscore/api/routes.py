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
    PluginListResponse,
    PluginResponse,
    ReportListResponse,
    SavedReportResponse,
    TrainingStatusResponse,
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
    weights: str | None = Query(
        None,
        description="Custom weights t:a:c:f (e.g. 25:30:25:20)",
        pattern=r"^\d+(\.\d+)?:\d+(\.\d+)?:\d+(\.\d+)?:\d+(\.\d+)?$",
    ),
    db: SupabaseClient = Depends(_require_supabase),
):
    """Upload an image, run analysis, store image and report in Supabase."""
    suffix = _validate_extension(file.filename)
    content = await _read_upload(file)
    report, warnings = await _run_analysis(content, suffix, request, skip_ai, weights)

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
    errors_json: str = Form("{}"),
    db: SupabaseClient = Depends(_require_supabase),
):
    """Save multiple already-analyzed reports as a batch."""
    import json
    from visionscore.models import AnalysisReport

    try:
        reports_map = json.loads(reports_json)
    except Exception:
        raise HTTPException(400, "Invalid reports JSON")

    try:
        errors_map: dict[str, str] = json.loads(errors_json) if errors_json else {}
    except Exception:
        errors_map = {}

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

    # Persist error records for failed images
    errors_saved = 0
    if errors_map:
        errors_saved = await db.save_batch_errors(errors_map, batch_id)

    if saved_count == 0 and errors_saved == 0:
        raise HTTPException(400, "No reports could be saved")

    return BatchSaveResponse(
        batch_id=batch_id, saved_count=saved_count, errors_saved=errors_saved
    )


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


# ---------------------------------------------------------------------------
# Plugin routes
# ---------------------------------------------------------------------------

def _build_plugin_registry(request: Request):
    """Build a plugin registry with all discovered plugins."""
    from visionscore.plugins import register_bundled_plugins
    from visionscore.plugins.registry import PluginRegistry

    settings = request.app.state.settings
    registry = PluginRegistry()
    registry.discover_entry_points()
    if settings.plugin_dir and settings.plugin_dir.is_dir():
        registry.discover_directory(settings.plugin_dir)

    bundled_enabled = settings.enable_bundled_plugins
    if bundled_enabled:
        register_bundled_plugins(registry)

    return registry, bundled_enabled


@router.get(
    "/plugins",
    response_model=PluginListResponse,
    tags=["plugins"],
    summary="List registered plugins",
)
async def list_plugins(request: Request):
    """List all discovered and registered analyzer plugins."""
    registry, bundled_enabled = _build_plugin_registry(request)
    plugins = []
    for info, _cls in registry.get_all():
        plugins.append(
            PluginResponse(
                name=info.name,
                display_name=info.display_name,
                version=info.version,
                description=info.description,
                score_weight=info.score_weight,
                score_field=info.score_field,
                source="bundled" if bundled_enabled else "external",
            )
        )
    return PluginListResponse(plugins=plugins, bundled_enabled=bundled_enabled)


@router.post(
    "/plugins/toggle-bundled",
    tags=["plugins"],
    summary="Toggle bundled plugins on/off",
)
async def toggle_bundled_plugins(request: Request):
    """Toggle the enable_bundled_plugins setting at runtime."""
    settings = request.app.state.settings
    new_val = not settings.enable_bundled_plugins
    request.app.state.settings = settings.model_copy(
        update={"enable_bundled_plugins": new_val}
    )
    return {"enable_bundled_plugins": new_val}


# ---------------------------------------------------------------------------
# Training routes
# ---------------------------------------------------------------------------

_training_state: dict = {"running": False, "progress": {}}


@router.get(
    "/training/status",
    response_model=TrainingStatusResponse,
    tags=["training"],
    summary="Get training job status",
)
async def training_status():
    """Return the current training job status."""
    return TrainingStatusResponse(
        running=_training_state["running"],
        progress=_training_state["progress"],
    )


@router.post(
    "/training/start",
    tags=["training"],
    summary="Start a NIMA fine-tuning job",
    responses={
        400: {"description": "Invalid configuration or missing files"},
        409: {"description": "Training already in progress"},
    },
)
async def start_training(
    request: Request,
    csv_file: UploadFile = File(...),
    image_files: list[UploadFile] = File(...),
    epochs: int = Query(20, ge=1, le=200),
    batch_size: int = Query(16, ge=1, le=128),
    learning_rate: float = Query(1e-4, gt=0),
    val_split: float = Query(0.2, ge=0.05, le=0.5),
    full_finetune: bool = Query(False),
    augment: bool = Query(True),
    scale: str = Query("ava", pattern=r"^(ava|visionscore)$"),
):
    """Upload training images + CSV and start a NIMA fine-tuning job."""
    import shutil

    if _training_state["running"]:
        raise HTTPException(409, "Training already in progress")

    settings = request.app.state.settings

    # Create a temp directory with training images
    train_dir = Path(tempfile.mkdtemp(prefix="vs_train_"))
    csv_path = train_dir / "ratings.csv"

    try:
        # Save CSV
        csv_content = await csv_file.read()
        if not csv_content:
            raise HTTPException(400, "CSV file is empty")
        csv_path.write_bytes(csv_content)

        # Save images
        for img_file in image_files:
            if not img_file.filename:
                continue
            img_content = await img_file.read()
            (train_dir / img_file.filename).write_bytes(img_content)
    except HTTPException:
        raise
    except Exception as e:
        shutil.rmtree(train_dir, ignore_errors=True)
        raise HTTPException(400, f"Failed to process uploads: {e}")

    output_path = settings.model_dir / "nima_finetuned.pth"

    _training_state["running"] = True
    _training_state["progress"] = {
        "status": "starting",
        "epochs": epochs,
        "current_epoch": 0,
    }

    async def _run_training():
        from visionscore.training.trainer import NIMAAestheticTrainer, TrainingConfig

        try:
            config = TrainingConfig(
                image_dir=train_dir,
                csv_path=csv_path,
                output_path=output_path,
                base_weights=settings.custom_model_path,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                val_split=val_split,
                full_finetune=full_finetune,
                augment=augment,
                scale=scale,
            )
            trainer = NIMAAestheticTrainer(config)
            result = await asyncio.to_thread(trainer.train)
            _training_state["progress"] = {
                "status": "completed",
                "epochs": result.epochs_trained,
                "current_epoch": result.epochs_trained,
                "best_epoch": result.best_epoch,
                "best_val_loss": result.best_val_loss,
                "final_train_loss": result.final_train_loss,
                "final_val_loss": result.final_val_loss,
                "training_time_seconds": result.training_time_seconds,
                "total_images": result.total_images,
                "output_path": result.output_path,
            }
        except Exception as e:
            _training_state["progress"] = {
                "status": "failed",
                "error": str(e),
            }
        finally:
            _training_state["running"] = False
            shutil.rmtree(train_dir, ignore_errors=True)

    asyncio.create_task(_run_training())

    return {
        "detail": "Training started",
        "epochs": epochs,
        "image_count": len(image_files),
        "output_path": str(output_path),
    }
