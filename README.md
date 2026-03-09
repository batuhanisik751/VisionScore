# VisionScore

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AI-powered photo evaluation tool that scores images on technical quality, aesthetics, composition, and provides natural language feedback.

## Features

- **HEIC/HEIF Support** -- Analyze Apple HEIC photos directly (requires `pillow-heif`)
- **Technical Quality** -- Sharpness, exposure, noise, dynamic range
- **Aesthetic Scoring** -- NIMA (MobileNetV2) trained on AVA dataset
- **Composition Analysis** -- Rule of thirds, subject position, horizon, balance
- **AI Feedback** -- Ollama + LLaVA for natural language critique
- **Score Aggregation** -- Weighted scoring, grades S/A/B/C/D/F
- **Comparison & Batch** -- Side-by-side image comparison, directory batch analysis with CSV export
- **Fine-Tuning** -- Train NIMA on your own rated images with EMD loss, augmentation, and LR scheduling
- **REST API** -- FastAPI with Supabase persistence
- **Web Dashboard** -- React + Vite + Tailwind frontend

## Quick Start

```bash
pip install -e ".[dev,api]"
python scripts/download_models.py
visionscore analyze photo.jpg
```

## CLI Usage

```bash
visionscore analyze photo.jpg                        # Rich terminal output
visionscore analyze photo.jpg --output json          # JSON output
visionscore analyze photo.jpg --save report.md       # Save markdown report
visionscore analyze photo.jpg --weights 30:30:30:10  # Custom weights (t:a:c:ai)
visionscore analyze photo.jpg --skip-ai              # Skip AI feedback
visionscore info photo.jpg                           # EXIF metadata
visionscore compare before.jpg after.jpg             # Compare two images
visionscore analyze-batch photos/ --skip-ai          # Batch analysis
visionscore analyze-batch photos/ --save results.csv # Export CSV
```

## Training

Fine-tune NIMA on your own rated images (`filename,score` CSV). Trained weights in `~/.visionscore/models/` are loaded automatically.

```bash
visionscore train photos/ ratings.csv --epochs 20
visionscore train photos/ ratings.csv --scale visionscore --full --lr 5e-5
```

Options: `--epochs`, `--batch-size`, `--lr`, `--val-split`, `--full`, `--no-augment`, `--scale`, `--seed`.

## API Usage

```bash
uvicorn visionscore.api.app:app --reload
curl -X POST http://localhost:8000/api/v1/analyze -F "file=@photo.jpg"
```

Full API docs at `http://localhost:8000/docs`. Config via env vars or `.env` file -- see `.env.example`.

## Plugins

VisionScore supports analyzer plugins that extend the scoring pipeline. Plugins are `BaseAnalyzer` subclasses with a `plugin_info` class variable.

### Bundled Plugins

- **Instagram Readiness** -- Evaluates aspect ratio, resolution, and saturation for Instagram fit. Enable with `ENABLE_BUNDLED_PLUGINS=true`.

### Creating a Custom Plugin

Create a `.py` file in `~/.visionscore/plugins/` (or set `PLUGIN_DIR`):

```python
from pydantic import BaseModel
from visionscore.analyzers.base import BaseAnalyzer
from visionscore.plugins.info import PluginInfo

class MyResult(BaseModel):
    overall: float = 0.0

class MyPlugin(BaseAnalyzer):
    plugin_info = PluginInfo(name="my_plugin", display_name="My Plugin")

    def analyze(self, image, metadata=None):
        return MyResult(overall=85.0)
```

Plugins can also be distributed as packages using the `visionscore.analyzers` entry-point group. List registered plugins with `visionscore plugins`.

## Project Structure

```
src/visionscore/
  analyzers/       # Technical, aesthetic, composition, AI feedback
  pipeline/        # Image loading, metadata, orchestration
  scoring/         # Score aggregation, grading
  output/          # JSON, CLI, markdown, CSV reports
  training/        # NIMA fine-tuning pipeline
  plugins/         # Plugin system (registry, info, bundled plugins)
  api/             # FastAPI + Supabase client
frontend/          # React + Vite + Tailwind dashboard
tests/             # pytest test suite
scripts/           # Model download
```

## Development

```bash
pytest                          # Run tests
ruff check src/ tests/          # Lint
ruff format src/ tests/         # Format
mypy src/visionscore/           # Type check
```

## License

[MIT](LICENSE)
