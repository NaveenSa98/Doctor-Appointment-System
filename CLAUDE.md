# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Appointment Manager

**Project Description:** A web application to manage doctors' appointments, including patient management, appointment scheduling, and doctor management.

## Tech Stack

- **Frontend:** React (Vite, JS), TanStack Query
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Postgres (Supabase)
- **Auth:** JWT

## Project Structure

```bash

Doctor-Appointment-System/
├── CLAUDE.md
├── docs/ (ARCHITECTURE.md = the plan and API contract, DECISIONS.md)
├── backend/ (own pyproject.toml, managed by uv)
│   ├── app/ (main.py, core/, db/, models/, schemas/,
│   │         repositories/, services/, api/v1/)
│   ├── alembic/
│   └── tests/ (unit/, api/, conftest.py)
├── frontend/
│   └── src/ (api/, components/, pages/, hooks/, utils/, __tests__/)
├── .github/workflows/ci.yml
├── .claude/ (commands/, settings.json)
├── README.md
└── .gitignore
```

Not all of this exists yet: see the milestones in `docs/ARCHITECTURE.md` (M0 done: backend foundation).

## Commands

All backend commands run from `backend/` through uv.

- Install: `uv sync`
- Database: Supabase Postgres. `DATABASE_URL` is the transaction pooler (app); `DATABASE_URL_MIGRATIONS` is the session pooler (Alembic and tests). Tests use a throwaway `test_<random>` schema.
- Backend: `uv run uvicorn app.main:create_app --factory --reload --no-access-log` (needs `backend/.env`, see `.env.example`; the access log stays off because query strings can contain patient names)
- Backend tests: `uv run pytest --cov=app --cov-fail-under=80` (single test: `uv run pytest tests/api/test_health.py::test_health_ok`)
- Lint/format: `uv run ruff check . && uv run ruff format .`
- Type check: `uv run mypy`
- Frontend: `cd frontend && npm run dev | npm test | npm run lint` (not created yet)
- DB migrate: `uv run alembic upgrade head` (not set up yet)

## Rules

- Layering: routers → services → repositories. No SQL in routers.
- Database access goes through the data layer, never directly from routes
- Type hints and docstrings on all public functions. Max function length ~40 lines.
- Routes/controllers stay thin; business logic lives in `services/`
- Frontend talks to the backend only through `api/v1/`
- All times stored in UTC; convert in the UI.
- Every feature ships with tests. Run tests and lint before declaring done.
- Small commits, conventional commit messages.
- Validate all input at the API boundary (Pydantic).
- Return consistent error shapes: `{ "error": { "code", "message", "details"? } }` (`details` only for 422 field errors).
- Booking (`POST /appointments`) and the doctor/hospital lookups are public; everything else needs sign-in. See the API contract in `docs/ARCHITECTURE.md`.

## Security

- Never log patient names or PII. Never commit secrets; use .env.
- Never log tokens, passwords, or personal data
- Use parameterized queries only; sanitize any user-rendered content
- Check authorization on every protected endpoint, not just authentication.

## Do Not

- Edit generated files or anything in `<migrations/applied, dist/, build/>`
- Modify `.env` files or commit credentials
- Add new dependencies without asking first
- Make breaking API changes without flagging them
