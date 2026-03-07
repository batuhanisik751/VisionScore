# VisionScore

AI-powered photo evaluation tool that analyzes images and produces meaningful scores and feedback on technical quality, aesthetics, composition, and more.

## Project Status

Phase 7 complete -- full analysis pipeline with FastAPI REST service and Supabase integration.

## What's Implemented

- **Technical Quality Analysis** - Sharpness (Laplacian + Sobel), exposure (LAB histogram), noise (Immerkaer), dynamic range (percentile)
- **Aesthetic Scoring (NIMA)** - MobileNetV2 trained on AVA dataset, score distribution analysis (mean, std dev, confidence), auto GPU/MPS/CPU detection
- **Composition Analysis** - Spectral residual saliency, rule of thirds, subject position, horizon detection, visual balance
- **AI Feedback** - Ollama + LLaVA vision LLM for natural language critique, genre classification, strengths/improvements, mood analysis. Graceful skip when Ollama unavailable.
- **Score Aggregation** - Weighted scoring across all analyzers with automatic weight redistribution for missing components. Grade system: S/A/B/C/D/F.
- **Pipeline Orchestrator** - Coordinates image loading, metadata extraction, analysis, scoring, and grading in one call.
- **CLI Tool** - `visionscore analyze photo.jpg` with overall score panel, category bars, detailed breakdowns. Flags: `--skip-ai`, `--weights`, `--save`, `--output`
- **Multiple Output Formats** - Rich terminal, JSON (`--output json`), Markdown (`--output markdown`), save to file (`--save report.json`)
- **Image Pipeline** - Loading, validation, resizing, EXIF metadata extraction
- **Model Download Script** - `python scripts/download_models.py` to fetch NIMA weights
- **REST API (FastAPI)** - `POST /analyze` for image upload + analysis, `POST /analyze/save` with Supabase persistence, reports CRUD, health check, Swagger UI at `/docs`
- **Supabase Integration** - Image storage, report persistence, graceful degradation when unconfigured

## Planned Features

- Batch analysis, web dashboard, image comparison

## Tech Stack

- Python 3.11+, PyTorch, torchvision, OpenCV, Pillow, NumPy
- Typer (CLI), FastAPI (REST API), Pydantic (data models), Rich (terminal output)
- Supabase (DB + Storage), Ollama + LLaVA (AI feedback)
- pytest, ruff, mypy

## Project Structure

```
src/visionscore/       # Main package
  analyzers/           # Technical, aesthetic, composition, AI feedback
  pipeline/            # Image loading, metadata, orchestration
  scoring/             # Score aggregation, grading
  output/              # JSON, CLI, markdown, visual reports
  api/                 # FastAPI web service + Supabase client
tests/                 # pytest test suite (155 tests)
scripts/               # Model download, benchmarks
sql/                   # Supabase schema (analysis_reports table)
docs/                  # API reference documentation
```

## Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/VisionScore.git
cd VisionScore

# Install in dev mode (with API support)
pip install -e ".[dev,api]"

# Download NIMA model weights
python scripts/download_models.py

# Analyze a photo
visionscore analyze photo.jpg

# JSON output
visionscore analyze photo.jpg --output json

# Save markdown report
visionscore analyze photo.jpg --save report.md

# Skip AI feedback, custom weights
visionscore analyze photo.jpg --skip-ai --weights 30:30:30:10

# View image metadata
visionscore info photo.jpg

# Start the API server
uvicorn visionscore.api.app:app --reload
# Then: curl -X POST http://localhost:8000/api/v1/analyze -F "file=@photo.jpg"
```

## Claude Code Integration

This project includes Claude Code automation:

- **Post-change hook** (`.claude/settings.json`) -- automatically triggers after source file edits
- **Post-change agent** (`.claude/agents/post-change.md`) -- creates tests, updates docs, suggests commit messages

## License

See [LICENSE](LICENSE) for details.
