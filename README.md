# VisionScore

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

AI-powered photo evaluation tool that scores images on technical quality, aesthetics, composition, and provides natural language feedback.

## Features

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

Fine-tune the NIMA aesthetic model on your own rated image dataset. Provide a directory of images and a CSV file with `filename,score` columns.

```bash
# Basic training (AVA 1-10 scale)
visionscore train photos/ ratings.csv --epochs 20

# VisionScore scale (0-100) with full backbone unfreezing
visionscore train photos/ ratings.csv --scale visionscore --full --lr 5e-5

# Custom output path and base weights
visionscore train photos/ ratings.csv -o my_model.pth --base-weights nima.pth
```

Options: `--epochs`, `--batch-size`, `--lr`, `--val-split`, `--full` (unfreeze backbone), `--no-augment`, `--scale` (ava/visionscore), `--seed`.

Trained weights are automatically used by the analyzer when placed in `~/.visionscore/models/`.

## API Usage

```bash
uvicorn visionscore.api.app:app --reload
curl -X POST http://localhost:8000/api/v1/analyze -F "file=@photo.jpg"
curl http://localhost:8000/api/v1/health
```

Full API docs at `http://localhost:8000/docs` (Swagger UI).

## Configuration

Environment variables (or `.env` file): `OLLAMA_HOST`, `OLLAMA_MODEL`, `SUPABASE_URL`, `SUPABASE_KEY`, `API_HOST`, `API_PORT`. See `.env.example`.

## Project Structure

```
src/visionscore/
  analyzers/       # Technical, aesthetic, composition, AI feedback
  pipeline/        # Image loading, metadata, orchestration
  scoring/         # Score aggregation, grading
  output/          # JSON, CLI, markdown, CSV reports
  training/        # NIMA fine-tuning pipeline
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
