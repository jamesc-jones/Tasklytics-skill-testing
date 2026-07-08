# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Two independently-run apps plus a reverse-proxy config, in one repo:

- `tasklytics-skill-testing-backend/` — FastAPI + SQLAlchemy + Alembic, Python 3.11
- `tasklytics-skill-testing-frontend/` — React 19 + Vite (plain JS/JSX, no TypeScript)
- `nginx/default.conf` — production reverse proxy (`/` → frontend:3000, `/api/` → backend:8000, with rate limiting)
- `docker-compose.yml` (repo root) — orchestrates backend, frontend, postgres, nginx. Its `build:` paths (`./tasklytics-backend`, `./tasklytics-frontend`) do **not** match the actual folder names (`tasklytics-skill-testing-backend`/`-frontend`), so this root compose file is currently broken/stale. Each app also has its own `docker-compose.yml` inside its own directory.

## Commands

### Backend — run from `tasklytics-skill-testing-backend/`

- Install deps: `pip install -r requirements.txt` (a `.venv` already exists in this folder)
- Run dev server: `uvicorn app.main:app --reload`
- Create a migration: `alembic revision --autogenerate -m "message"`
- Apply migrations: `alembic upgrade head`
- Run all tests: `python -m pytest tests/` (must be `python -m pytest`, not bare `pytest` — there's no `pyproject.toml`/`pytest.ini` setting `pythonpath`, so `-m` is what puts this directory's `app` package on `sys.path`)
- Run a single test: `python -m pytest tests/routes/test_chat.py::TestChatEndpointSuccess -v` (or `-k <name>`)
- Test tooling gap: `pytest`, `httpx`, and `anthropic` are required to import/run the suite but are **not yet declared in `requirements.txt`** — install them manually into `.venv` (`pip install pytest httpx anthropic`) until that's fixed. `anthropic` is required even just to import `app.main`, since `app/services/ai/claude_client.py` constructs an `anthropic.Anthropic()` client at module load time.

### Frontend — run from `tasklytics-skill-testing-frontend/`

- Install: `npm install`
- Dev server: `npm run dev` (Vite)
- Lint: `npm run lint`
- Build: `npm run build`
- Preview production build: `npm run preview`
- No test suite exists in this repo yet.

### Environment variables

Backend (`.env` locally, `.env.docker`/`.env.production` for deployment): `DATABASE_URL`, `SECRET_KEY`, `ENV`, `ANTHROPIC_API_KEY`, `TOGETHER_API_KEY`, `VOYAGE_API_KEY`. `DATABASE_URL` may point at SQLite (local dev — see `tasklytics.db`) or Postgres; `app/database.py` branches on the URL scheme. `ENV=docker` skips loading `.env` via `python-dotenv` (Docker injects env vars directly).

Frontend: `VITE_API_URL` (defaults to `/api`, see `src/api/config.js`).

## Architecture

### Auth

JWT bearer tokens (`python-jose`, HS256, signed with `SECRET_KEY`). Issued in `app/routes/auth.py` on login/register; verified per-request by `app/auth/auth_dependencies.py:get_current_user` (decodes token, loads `User` by id). `require_admin` wraps it to gate admin-only routes on `User.role == "admin"`. Frontend keeps the token in `localStorage` via `src/context/AuthContext.jsx` and passes it manually as a header on each call in `src/api/api.js` (plain `fetch`, not an axios instance/interceptor, despite axios being a dependency).

### Data model

Only two tables: `User` and `Task` (`app/models/`), 1-to-many via `Task.user_id`. Every task route filters by `user_id` for regular users and skips the filter for `role == "admin"`. Alembic migrations live in `alembic/versions/`, but `app/main.py` also calls `Base.metadata.create_all(bind=engine)` on every startup — so model/migration drift can go unnoticed in local dev (tables get created either way) and only surfaces in environments that rely solely on `alembic upgrade head`.

### Route registration and a routing conflict (`app/main.py`)

Routers are included in this order: `auth`, `tasks`, `admin`, `analytics`, `ai` (legacy), `chat`. Two of them both define `GET /tasks/analytics`:

- `app/routes/tasks.py` — correct, filters by `Task.user_id`.
- `app/routes/analytics.py` — dead code; filters by `Task.owner_id`, which doesn't exist on the `Task` model (field is `user_id`), so it would raise if ever reached.

Because `tasks.router` is registered first, FastAPI always resolves `/tasks/analytics` to the working handler; `routes/analytics.py`'s handler is unreachable. Keep this in mind before "fixing" one in isolation — check which one is actually being hit.

### Two parallel, independently-evolved AI subsystems

Don't assume these share code or conventions — they were built separately:

1. **`app/ai/`** (legacy, single-shot insights) — `POST /ai/task-insights`. `ai/client.py:call_llm` calls **Together AI** (`TOGETHER_API_KEY`, model `openai/gpt-oss-20b`) directly via `requests`, prompt built in `ai/prompts.py`.
2. **`app/ai_agents/` + `app/services/ai/`** (current, chat-based) — `POST /chat`, routed through `app/api/routes/chat.py` → `ai_agents/chat_agent.py:ChatAgent.run()`. Flow: fetch the user's tasks (`ai_agents/tools.py`) → compute productivity stats → build context (`services/ai/context_builder.py`) → call **Anthropic** directly via the `anthropic` SDK (`services/ai/claude_client.py`, hardcoded model `claude-sonnet-4-5`, `ANTHROPIC_API_KEY`) → parse the reply into structured JSON (`services/ai/response_parser.py`, schema in `app/models/chat_models.py`). The prompt demands raw JSON with no markdown fences — if you edit the prompt, keep `response_parser.py`'s stripping logic in sync (it currently only strips a leading ` ```json ` fence).

Default to extending `app/ai_agents/` + `app/services/ai/` for new chat/agent work; treat `app/ai/` as legacy unless told otherwise.

### Backend test setup (`tests/`)

Isolated per-test in-memory SQLite (`StaticPool` + `check_same_thread=False`) with `get_db` overridden via `app.dependency_overrides`; auth is exercised for real (a real JWT is minted for a seeded test user) rather than bypassed. The Anthropic call is mocked by patching `app.ai_agents.chat_agent.call_claude`, **not** `app.services.ai.claude_client.call_claude` — `chat_agent.py` does `from ... import call_claude`, binding its own local reference at import time, so patching the original definition doesn't affect what `ChatAgent.run()` actually calls. See `tests/conftest.py` for the shared fixtures (`db_session`, `client`, `test_user`, `auth_headers`, `mock_call_claude`) before adding new test modules.

### Frontend structure

- `src/api/` — one file per backend resource (`api.js`, `ai.js`, `analytics.js`), all built on `fetch` and reading the base URL from `src/api/config.js`. Auth token is passed explicitly into each call, not attached globally.
- `src/context/AuthContext.jsx` — holds the JWT in state + `localStorage`; note the token-reload-on-mount `useEffect` is currently commented out.
- `src/components/ProtectedRoute.jsx` — route guard reading `AuthContext`, used around `/dashboard` in `src/App.jsx`.
- `src/pages/` — routed views (`Login`, `Register`, `Dashboard`). `Dashboard` composes `TaskList`, `CreateTask`, `Analytics`, `TaskChart`, `AIInsights`.

## Notes

- `.claude/CLAUDE.md` (auto-loaded alongside this file) covers the project's tech stack summary, general dev principles, and PR/git standards — this file is the map of how the code actually fits together.
- `.claude/skills/pr-description/` implements the PR-description skill those standards reference.
