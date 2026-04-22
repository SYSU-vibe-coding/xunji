# Contributing

## Branch Strategy

- `main`: release-ready branch
- `develop`: integration branch
- `feature/<name>`: feature development
- `fix/<name>`: bug fix branch

## Working Agreement

1. Create or link an issue before coding.
2. Keep each pull request focused on one feature or one bug fix.
3. Update docs when API, database, or workflow changes.
4. Run the self-check before opening a PR (see root `CODEBUDDY.md`):
   - backend: `uv run ruff check .`, `uv run mypy app`, `uv run pytest`
   - frontend: `pnpm lint`, `pnpm test:unit`
5. DB schema changes must ship with an Alembic migration (`backend/alembic/versions/`).

## Commit Message

Use a short conventional style, include the related FR when relevant:

- `feat(FR-02): add lost item publish api`
- `fix(FR-05): correct claim review status transition`
- `refactor(claim): extract handover transaction into service`
- `test(match): cover score fallback path`
- `docs: update database model`
- `chore(ci): add ruff step`
