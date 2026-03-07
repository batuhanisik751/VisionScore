# VisionScore API Reference

## Base URL

```
http://localhost:8000/api/v1
```

Interactive Swagger docs are available at `http://localhost:8000/docs`.

## Running the Server

```bash
pip install -e ".[api]"
uvicorn visionscore.api.app:app --reload
```

## Endpoints

### Health Check

```
GET /api/v1/health
```

```bash
curl http://localhost:8000/api/v1/health
```

Response:
```json
{
  "status": "ok",
  "version": "0.1.0",
  "supabase_connected": false
}
```

### Analyze Image

```
POST /api/v1/analyze
```

Upload an image and receive a full quality analysis.

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "file=@photo.jpg"
```

Query parameters:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip_ai` | bool | false | Skip AI feedback analysis |
| `weights` | string | null | Custom weights `t:a:c:f` (e.g. `25:30:25:20`) |

Response: `AnalyzeResponse` with full `AnalysisReport` and warnings.

### Analyze and Save

```
POST /api/v1/analyze/save
```

Analyze an image and persist the report and image to Supabase.

```bash
curl -X POST http://localhost:8000/api/v1/analyze/save \
  -F "file=@photo.jpg"
```

Requires Supabase configuration (`SUPABASE_URL`, `SUPABASE_KEY`). Returns 503 if not configured.

### List Reports

```
GET /api/v1/reports?limit=20&offset=0
```

```bash
curl http://localhost:8000/api/v1/reports
```

Requires Supabase. Returns paginated list of saved reports.

### Get Report

```
GET /api/v1/reports/{report_id}
```

```bash
curl http://localhost:8000/api/v1/reports/550e8400-e29b-41d4-a716-446655440000
```

### Delete Report

```
DELETE /api/v1/reports/{report_id}
```

```bash
curl -X DELETE http://localhost:8000/api/v1/reports/550e8400-e29b-41d4-a716-446655440000
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Invalid file format, empty file, or bad parameters |
| 404 | Report not found |
| 413 | File too large (max 20MB) |
| 503 | Supabase not configured (for storage/report endpoints) |

## Configuration

Set these environment variables (or add to `.env`):

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
API_HOST=0.0.0.0
API_PORT=8000
```

The API works without Supabase for analysis-only mode (`POST /analyze`). Supabase is only required for report persistence endpoints.
