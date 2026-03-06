# VisionScore

AI-powered photo evaluation tool that analyzes images and produces meaningful scores and feedback on technical quality, aesthetics, composition, and more.

## Project Status

Phase 2 complete -- technical quality analysis is functional.

## What's Implemented

- **Technical Quality Analysis** - Sharpness (Laplacian + Sobel), exposure (LAB histogram), noise (Immerkaer), dynamic range (percentile)
- **CLI Tool** - `visionscore analyze photo.jpg` with colored score bars, `visionscore info` for metadata
- **Image Pipeline** - Loading, validation, resizing, EXIF metadata extraction
- **Multiple Output Formats** - Rich terminal output, JSON (`--output json`)

## Planned Features

- Aesthetic scoring (NIMA neural model)
- Composition analysis (rule of thirds, saliency, horizon, balance)
- AI feedback via Ollama + LLaVA (local, no API keys)
- REST API with Supabase (DB + Auth + Storage)

## Tech Stack

- Python 3.11+, OpenCV, Pillow, NumPy
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
