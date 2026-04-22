# Backend

Xunji main backend service. Python 3.12 + FastAPI + SQLAlchemy 2.x (async) + Alembic, managed by `uv`.

See the root `CODEBUDDY.md` for task-to-document routing, hard rules, and the full command reference.

## Current status

At the moment, only `pyproject.toml` and this README are committed in `backend/`. `app/`, `alembic/`, `tests/`, and `uv.lock` are target bootstrap artifacts, not files that already exist in this tree.

## Command contract (after scaffold lands)

Run the commands below after the backend scaffold has been added.

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
