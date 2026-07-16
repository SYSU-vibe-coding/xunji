# Xunji (寻迹) — Agent Guide

Campus lost-and-found platform, 5-person course project. Monorepo with P0/P1 already implemented (not a scaffold). **Read `CODEBUDDY.md` first** — it is the authoritative rules file with task→doc routing, the full hard-rule list, and an exhaustive command reference. This file captures only what is easy to get wrong.

## Modules & entrypoints

- `backend/` — FastAPI main service, Python 3.12 + `uv`. App entry `app.main:app` (dev port 8080). Real `app/` modules: `user`, `item`, `match`, `claim`, `credit`, `notification`, `admin`, `job`, `operation_log`, `core`, `common`, `db` (note: `job/` and `operation_log/` exist in code but not in `CODEBUDDY.md`'s doc tree).
- `ai-service/` — FastAI helper, **separate process** (dev port 5000). Entry `app.main:app`. Called by backend over HTTP under `/internal/ai/*`. Does **not** connect to business MySQL; never persists business state.
- `frontend/user-app/` (dev port 5173) and `frontend/admin-web/` (dev port 5174) — Vue 3 + Vite + Pinia. `frontend/shared/` holds shared API types/consts.
- `deploy/docker/` — compose files + env templates. `docs/` — index at `docs/README.md`.

## Commands

```bash
# backend
cd backend && uv sync
uv run uvicorn app.main:app --reload --port 8080
uv run alembic upgrade head                       # apply migrations
uv run alembic revision --autogenerate -m "msg"   # generate migration
uv run pytest tests/unit/claim/test_service.py::test_handover_confirm   # single test

# ai-service
cd ai-service && uv sync
uv run uvicorn app.main:app --reload --port 5000

# frontend (user-app or admin-web)
cd frontend/user-app && pnpm install && pnpm dev
pnpm test:unit -- FileName                        # filter vitest

# local deps only
cd deploy && docker compose up -d mysql minio
```

## Verification gate — run before considering work done (order matters)

Mirrors `.github/workflows/ci.yml`. CI runs on `main`/`develop` pushes and PRs.

- backend: `uv run ruff check .` → `uv run ruff format --check .` → `uv run mypy app` → `uv run pytest --cov=app`
- ai-service: `uv run ruff check .` → `uv run ruff format --check .` → `uv run mypy app` → `uv run pytest`
- frontend: `pnpm lint` → `pnpm test:unit --run` → `pnpm build`

`ruff format --check` is enforced in CI but **not** in `CODEBUDDY.md`'s self-check — run `uv run ruff format .` to autofix. `mypy` runs in `strict` mode.

## Easy-to-miss facts

- **Backend tests are fully offline.** `backend/tests/conftest.py` uses in-memory SQLite (`aiosqlite`) and monkeypatches MinIO, so `uv run pytest` needs no MySQL/MinIO. `asyncio_mode = "auto"` — async test functions need no `@pytest.mark.asyncio` decorator. Markers: `slow`, `integration` (backend); `slow`, `model` (ai-service); `--strict-markers` is on, so unknown marks error.
- **Backend startup validates security.** `lifespan` calls `settings.validate_startup_security()` and refuses placeholder `JWT_SECRET_KEY`/`ADMIN_PASSWORD` unless `DEBUG=true`. Admin bootstrap is gated by `BOOTSTRAP_ADMIN_ENABLED=false` — enable only for the intended first bootstrap. CORS defaults closed; allowlist via `CORS_ALLOWED_ORIGINS`.
- **Item publish uses a durable-jobs DB outbox** (`app/job/`). `BackgroundTasks` only wakes the poller; pending and retryable jobs survive process restarts. Do not replace this with fire-and-forget background calls. Tunables: `DURABLE_JOB_POLL_SECONDS`, `DURABLE_JOB_MAX_ATTEMPTS`, `DURABLE_JOB_RETRY_BASE_SECONDS`, `DURABLE_JOB_LOCK_TIMEOUT_SECONDS`, `SENSITIVE_JOB_MAX_CONCURRENCY`.
- **AI service auth/SSRF rules.** Every `/internal/ai/*` request must send `X-Service-Token` (≥32 chars); empty token is accepted only with `AI_LOCAL_DEV_MODE=true`. Image URLs must match `AI_ALLOWED_IMAGE_HOSTS` (exact or `*.suffix`); private IPs / single-label container names are rejected unless they exactly match `AI_TRUSTED_PRIVATE_IMAGE_HOSTS` (no wildcards). Leave `DASHSCOPE_API_KEY` empty to run the rule-based keyword baseline (used in CI / offline dev).
- **Frontend `pnpm lint` is `vue-tsc --noEmit`** (typecheck only — there is no eslint). `pnpm build` also typechecks (`vue-tsc --noEmit && vite build`). Auto-imports are via `unplugin-auto-import` / `unplugin-vue-components` (see `auto-imports.d.ts`, `components.d.ts`).
- **Legacy DB migration gotcha.** DBs created from the old handwritten `backend/sql/schema.sql` must be backed up and structurally compared against the full Alembic history before a one-time `alembic stamp head`. Never stamp an unverified schema; clean deploys use `alembic upgrade head` directly.
- Coverage omits `app/main.py` and `alembic/*`.

## Hard rules (full list in `CODEBUDDY.md` §硬性规则 — violating these means rework)

- Layering: `router → service → repository`. Routers never import `repository` or session. Cross-module: import only another module's `service`/`schemas`, never its `repository`/`models`.
- All business PKs are **ULIDs** (`CHAR(26)`) generated in the service layer — no autoincrement, no snowflake.
- ORM models and pydantic schemas are never the same class; return schemas from routers via `model_validate`.
- Multi-table writes (claim/handover/confirm) must be wrapped in `async with session.begin():`.
- Enums only from `docs/architecture/enums.md`; JSON `camelCase`, DB columns `snake_case`; response envelope `{code, message, data, requestId, timestamp}`.
- AI service failures must not roll back main-backend transactions — degrade per `docs/api/ai-service.md`.
- Change docs **before** code when API/enum/DB/workflow changes. DB schema changes must ship an `alembic/versions/` migration.

## Branching & commits

Branch from `develop` (`feature/<name>`, `fix/<name>`). Conventional commits with FR id, e.g. `feat(FR-02): add lost item publish api`. PRs: single focus, link the FR/issue, include test evidence and UI screenshots. For changes touching the P0 flow (login → publish → search → match → claim → handover → review), cover the relevant path in `docs/testing/`.
