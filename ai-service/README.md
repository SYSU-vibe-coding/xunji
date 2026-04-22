# AI Service

Xunji AI helper service. Python 3.12 + FastAPI, managed by `uv`. Independent process from the main backend; called via HTTP under `/internal/ai/*`.

Responsibilities:

- item image classification
- text/image similarity scoring (used by `matching-rules.md §1`)
- sensitive item detection and masking support

See `docs/api/ai-service.md` for the contract with the main backend, and `docs/architecture/matching-rules.md` for scoring rules.

## Quick commands

```bash
uv sync
uv run uvicorn app.main:app --reload --port 5000
uv run pytest
uv run pytest tests/test_match.py::test_score
uv run ruff check .
uv run ruff format .
uv run mypy app
```

## Layout

```
app/
  main.py
  routers/
    classify.py
    sensitive.py
    match.py
  services/
  models/        # inference wrappers, not weights
  schemas.py
tests/
models/          # model weights & download scripts (ignored by git if large)
docs/            # model selection / evaluation notes
```

## Boundaries

- Does **not** connect to the business MySQL
- Returns pure computation results; never persists business state
- Failures must not bubble up to break main-backend transactions — main backend falls back to rule-based scoring (see `matching-rules.md §2`)
