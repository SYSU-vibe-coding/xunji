# Backend

Xunji main backend service. Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic, managed by `uv`.

See the root `CODEBUDDY.md` for task-to-document routing, hard rules, and the full command reference.

## Current status

The backend scaffold has landed with FastAPI application wiring, SQLAlchemy async DB
session setup, Alembic configuration, user/auth APIs, item publish/search APIs,
operation logs, SQL schema, and focused unit tests.

## Command contract

```bash
# setup
uv sync

# run
uv run uvicorn app.main:app --reload --port 8080

# migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"

# tests
uv run pytest
uv run pytest tests/unit/claim/test_service.py::test_handover_confirm
uv run pytest --cov=app --cov-report=term-missing

# quality
uv run ruff check .
uv run ruff format .
uv run mypy app
```

Runtime startup rejects the repository's placeholder JWT/admin passwords unless `DEBUG=true` explicitly marks local development. Administrator creation is separately gated by `BOOTSTRAP_ADMIN_ENABLED=false`; enable it only for the intended first bootstrap. CORS defaults to no cross-origin access and accepts only the comma-separated `CORS_ALLOWED_ORIGINS` allowlist.

Item publication uses the `durable_jobs` database outbox. The lifespan runner is configured by `DURABLE_JOB_POLL_SECONDS` (default `1`), `DURABLE_JOB_MAX_ATTEMPTS` (`5`), `DURABLE_JOB_RETRY_BASE_SECONDS` (`5`), `DURABLE_JOB_LOCK_TIMEOUT_SECONDS` (`300`), and `SENSITIVE_JOB_MAX_CONCURRENCY` (`3`). `BackgroundTasks` only wakes the poller; pending and retryable work survives process restarts.

Databases created by the old handwritten `sql/schema.sql` must be backed up and structurally compared with the complete Alembic history before a one-time `alembic stamp head`. Never stamp an unverified schema; clean deployments should use `alembic upgrade head` directly.

## Target module layout

Each module under `app/` should follow a fixed layout: `router.py` / `service.py` / `repository.py` / `models.py` / `schemas.py` / `deps.py`. See `docs/architecture/module-design.md §3`.

```
app/
  main.py
  core/      config, logging, auth deps, exception handlers
  common/    response envelope, pagination, base exceptions, utils
  db/        Base, engine, AsyncSession factory, ULID helper
  user/      user & certification
  item/      lost/found items, search, upload
  match/     match tasks & results
  claim/     claims, verification, handover
  credit/    credit logs
  notification/
  admin/
```

## Hard rules (excerpt)

- Router → service → repository. Router never imports repository or session.
- Cross-module: only `service` and `schemas` of other modules. No sharing of `repository` / `models`.
- Primary keys are ULIDs (`CHAR(26)`) generated in service layer.
- ORM and pydantic schemas are never the same class.
- All routes `async def`; DB via `AsyncSession`; HTTP via `httpx.AsyncClient`.
- Multi-table writes require explicit `async with session.begin():`.

Full list is in root `CODEBUDDY.md`.
