# VisionScore

AI-powered photo evaluation tool that analyzes images and produces meaningful scores and feedback on technical quality, aesthetics, composition, and more.

## Project Status

Early stage -- project structure and tooling are set up. Implementation has not started yet.

## Planned Features

- **Technical Quality Analysis** - Sharpness, exposure, noise, dynamic range
- **Aesthetic Scoring** - Neural image assessment (NIMA) model
- **Composition Analysis** - Rule of thirds, saliency, horizon detection, visual balance
- **AI Feedback** - Natural language critique via vision LLMs (GPT-4o / Gemini)
- **CLI Tool** - `visionscore analyze photo.jpg` with rich terminal output
- **REST API** - FastAPI service for programmatic access
- **Multiple Output Formats** - JSON, Markdown, CLI summary

## Tech Stack

- Python 3.11+, PyTorch, OpenCV, Pillow
- Typer (CLI), FastAPI (API), Pydantic (data models)
- NIMA (MobileNetV2), YOLOv8, GPT-4o / Gemini Vision
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

# Install in dev mode (once pyproject.toml is created)
pip install -e ".[dev]"
```

## Claude Code Integration

This project includes Claude Code automation:

- **Post-change hook** (`.claude/settings.json`) -- automatically triggers after source file edits
- **Post-change agent** (`.claude/agents/post-change.md`) -- creates tests, updates docs, suggests commit messages

## License

See [LICENSE](LICENSE) for details.
