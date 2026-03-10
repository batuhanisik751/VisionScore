# VisionScore - Project Instructions

## Project
Python AI photo evaluation tool. Scores images on technical quality, aesthetics, composition, and provides AI feedback.

## Tech Stack
- Python 3.11+, PyTorch, OpenCV, Pillow, Typer (CLI), FastAPI (API)
- NIMA (MobileNetV2) for aesthetics, Ollama + LLaVA for AI feedback
- React 18 + TypeScript + Vite + Tailwind (frontend)
- pytest, ruff, mypy

## Structure
- `src/visionscore/` - main package (analyzers/, pipeline/, scoring/, output/, api/, training/, plugins/)
- `frontend/` - React web dashboard
- `tests/` - pytest tests with generated fixture images
- `scripts/` - model download, benchmarks
- `PLAN.md` - detailed implementation plan (gitignored)

## Conventions
- All analyzers extend `BaseAnalyzer` with an `analyze()` method
- Pydantic models for all data structures
- Async pipeline orchestration
- Scores are 0-100, grades S/A/B/C/D/F

## Subagent Policy
- Use subagents (Agent tool with Explore type) for investigating unfamiliar parts of the codebase
- Use subagents for researching external API patterns or library usage
- Do NOT read more than 5 files directly in the main context -- delegate to subagents instead

## Post-Change Hook
A hook in `.claude/settings.json` fires after every Edit/Write to `src/visionscore/**/*.py`.
When the hook triggers, follow `.claude/agents/post-change.md` exactly:
1. Create/run tests for the changed code
2. Update README.md and .gitignore if needed
3. Output a `COMMIT: <3-6 words>` commit message suggestion

## Compaction Rules
When compacting, always preserve:
- The full list of modified files in the current session
- All test commands that have been run and their pass/fail status
- The current phase/step being worked on from PLAN.md
