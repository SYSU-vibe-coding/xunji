# Repository Guidelines

## Project Structure & Module Organization
This repository is a monorepo for the Xunji campus lost-and-found platform. Keep work inside the existing top-level modules: `frontend/` for Vue apps, `backend/` for the FastAPI main service, `ai-service/` for the independent AI service, `deploy/` for environment templates and local deployment assets, and `docs/` for API, architecture, and testing documents. Current source code is still scaffold-light; treat `docs/architecture/module-design.md` as the target layout when adding `backend/app/`, `backend/tests/`, or `ai-service/app/`.

## Build, Test, and Development Commands
Use the documented command contract when scaffolding or extending modules:

- `cd backend && uv sync`: install backend dependencies
- `cd backend && uv run uvicorn app.main:app --reload --port 8080`: run the main backend
- `cd backend && uv run alembic upgrade head`: apply DB migrations
- `cd backend && uv run pytest`: run backend tests
- `cd backend && uv run ruff check . && uv run mypy app`: lint and type-check backend code
- `cd ai-service && uv sync && uv run uvicorn app.main:app --reload --port 5000`: run the AI service
- `cd frontend/user-app && pnpm install && pnpm dev`: run the user frontend
- `cd frontend/admin-web && pnpm install && pnpm dev`: run the admin frontend

## Coding Style & Naming Conventions
Follow repo rules from `CODEBUDDY.md` and `docs/api/conventions.md`. Use `camelCase` for JSON, `snake_case` for DB columns, and enum values only from `docs/architecture/enums.md`. Backend structure is `router -> service -> repository`; routers must not import repositories directly. Keep SQLAlchemy models and pydantic schemas separate. Prefer explicit async code, type annotations, and Ruff-clean formatting.

## Testing Guidelines
Backend tests use `pytest`; expected locations are `backend/tests/unit/` and `backend/tests/integration/`. Name Python tests `test_*.py`; frontend tests should follow `*.spec.ts`. Before opening a PR, rerun the relevant module tests and cover the P0 flow documented in `docs/testing/`: login, publish, search, match, claim, handover, and review.

## Commit & Pull Request Guidelines
Branch from `develop` using `feature/<name>` or `fix/<name>`. Follow short conventional commits such as `feat(FR-02): add lost item publish api` or `docs: update database model`. Keep each PR focused, link the issue or FR item, summarize test evidence, and include screenshots for UI changes. If you change APIs, enums, database fields, or workflows, update the matching docs in the same PR.
