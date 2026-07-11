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

## Internal API security

`GET /health` is unauthenticated for probes. Every `/internal/ai/*` request
must send `X-Service-Token: <AI_SERVICE_TOKEN>`. `AI_SERVICE_TOKEN` must be at
least 32 characters; an empty token is accepted only when
`AI_LOCAL_DEV_MODE=true` is explicitly configured for isolated local use.

Image inputs use `http` or `https`. Public storage hosts must match
`AI_ALLOWED_IMAGE_HOSTS`, a comma-separated list of exact hosts or `*.suffix`
entries. Private IPs and single-label container names are rejected unless the
host exactly matches `AI_TRUSTED_PRIVATE_IMAGE_HOSTS`; this dedicated list does
not accept wildcards and should contain only controlled storage such as
`minio`. Credentials remain forbidden. The VL client repeats validation
immediately before passing a URL to the model provider.

Sensitive detection currently does not create a redacted object. A sensitive
or fallback result therefore returns `maskedImageUrl: null`; incomplete or
failed detection returns `degraded: true` and `needsReview: true`. Fallback is
fail-closed (`isSensitive: true`) so callers do not publish an unreviewed image
as safe.

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
