# VisionScore

AI-powered photo evaluation tool that analyzes images and produces meaningful scores and feedback on technical quality, aesthetics, composition, and more.

## Project Status

Phase 5 complete -- technical quality, aesthetic scoring, composition analysis, and AI feedback are functional.

## What's Implemented

- **Technical Quality Analysis** - Sharpness (Laplacian + Sobel), exposure (LAB histogram), noise (Immerkaer), dynamic range (percentile)
- **Aesthetic Scoring (NIMA)** - MobileNetV2 trained on AVA dataset, score distribution analysis (mean, std dev, confidence), auto GPU/MPS/CPU detection
- **Composition Analysis** - Spectral residual saliency, rule of thirds, subject position, horizon detection, visual balance
- **CLI Tool** - `visionscore analyze photo.jpg` with colored score bars, `visionscore info` for metadata
- **Image Pipeline** - Loading, validation, resizing, EXIF metadata extraction
- **Model Download Script** - `python scripts/download_models.py` to fetch NIMA weights
- **AI Feedback** - Ollama + LLaVA vision LLM for natural language critique, genre classification, strengths/improvements, mood analysis. Graceful skip when Ollama unavailable.
- **Multiple Output Formats** - Rich terminal output, JSON (`--output json`)

## Planned Features

- Score aggregation, grading system, and polished report generation
- REST API with Supabase (DB + Auth + Storage)

## Tech Stack

- Python 3.11+, PyTorch, torchvision, OpenCV, Pillow, NumPy
- Typer (CLI), Pydantic (data models), Rich (terminal output)
- pytest, ruff, mypy

## Project Structure

```
src/visionscore/       # Main package
  analyzers/           # Technical, aesthetic, composition, AI feedback
  pipeline/            # Image loading, metadata, orchestration
  scoring/             # Score aggregation, grading
  output/              # JSON, CLI, markdown, visual reports
  api/                 # FastAPI web service
tests/                 # pytest test suite
scripts/               # Model download, benchmarks
```

## Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/VisionScore.git
cd VisionScore

# Install in dev mode
pip install -e ".[dev]"

# Download NIMA model weights
python scripts/download_models.py

# Analyze a photo
visionscore analyze photo.jpg

# View image metadata
visionscore info photo.jpg
```

## Claude Code Integration

This project includes Claude Code automation:

- **Post-change hook** (`.claude/settings.json`) -- automatically triggers after source file edits
- **Post-change agent** (`.claude/agents/post-change.md`) -- creates tests, updates docs, suggests commit messages

## License

See [LICENSE](LICENSE) for details.
