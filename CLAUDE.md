# Recipe Aggregator

## Recovery
After compaction or session start:
- Read this file and `README.md`.
- Check `git status --short --branch` before editing.

## Commands
- Run tests: `pytest`
- Run lint: `ruff check`
- Start API locally: `uvicorn backend.main:app --reload`

## Testing
- Tests live in `tests/`.
- Add focused pytest coverage for backend services, routers, and scripts when behavior changes.

## Structure
- `backend/`: FastAPI app, models, database, routers, services, and prompts.
- `scripts/`: command-line ingestion and maintenance tools.
- `frontend/`: static frontend assets.
- `tests/`: pytest suite.

## Conventions
- Keep backend behavior changes small and covered by pytest where practical.
- Avoid committing local data files, credentials, browser sessions, or generated caches.
