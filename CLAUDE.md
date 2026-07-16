# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Two independently-run apps plus a reverse-proxy config, in one repo:

- `tasklytics-skill-testing-backend/` — FastAPI + SQLAlchemy + Alembic, Python 3.11
- `tasklytics-skill-testing-frontend/` — React 19 + Vite (plain JS/JSX, no TypeScript)
- `nginx/default.conf` — reverse proxy (`/` → frontend:3000, `/api/` → backend:8000, with rate limiting + a block on `.env`/`.git` paths). Currently **HTTP-only, no TLS** — it was stripped down to a local-dev config because the previous version required Let's Encrypt certs that don't exist locally. If deploying to a real host, restore HTTPS (or add a separate prod config) before going live; don't assume this file is production-ready as-is.
- `docker-compose.yml` (repo root) — orchestrates backend, frontend, postgres, nginx; builds paths now correctly point at `tasklytics-skill-testing-backend`/`-frontend`. Only `nginx` publishes a host port (`80:80`); backend/frontend/db use `expose` only and are reachable solely over the Compose network. Backend/frontend each read their env from `.env.docker`/`.env` via `env_file:` (see `tasklytics-skill-testing-backend/.env.docker.example` for the template and required var names). Note: the `db` service's `POSTGRES_PASSWORD` is currently a real value hardcoded directly in this committed compose file, not sourced from an env file — treat it as already-exposed and rotate/parameterize before any real deployment. Each app also has its own `docker-compose.yml` inside its own directory, independent of this root one.

## Commands

### Backend — run from `tasklytics-skill-testing-backend/`

- Install deps: `pip install -r requirements.txt` (a `.venv` already exists in this folder)
- Run dev server: `uvicorn app.main:app --reload`
- Create a migration: `alembic revision --autogenerate -m "message"`
- Apply migrations: `alembic upgrade head`
- Run all tests: `python -m pytest tests/` (must be `python -m pytest`, not bare `pytest` — there's no `pyproject.toml`/`pytest.ini` setting `pythonpath`, so `-m` is what puts this directory's `app` package on `sys.path`)
- Run a single test: `python -m pytest tests/routes/test_chat.py::TestChatEndpointSuccess -v` (or `-k <name>`)
- `pytest`, `httpx`, and `anthropic` are declared in `requirements.txt`, so a plain `pip install -r requirements.txt` covers both running the app and running the test suite. `anthropic` is required even just to import `app.main`, since `app/services/ai/claude_client.py` constructs an `anthropic.Anthropic()` client at module load time — a missing/invalid `ANTHROPIC_API_KEY` breaks app startup, not just chat requests.

### Frontend — run from `tasklytics-skill-testing-frontend/`

- Install: `npm install`
- Dev server: `npm run dev` (Vite)
- Lint: `npm run lint`
- Build: `npm run build`
- Preview production build: `npm run preview`
- No test suite exists in this repo yet.

### Environment variables

Backend (`.env` locally, `.env.docker`/`.env.production` for deployment — all gitignored except the `.env.docker.example` template): `DATABASE_URL`, `SECRET_KEY`, `ENV`, `ANTHROPIC_API_KEY`, `TOGETHER_API_KEY`, `VOYAGE_API_KEY`. `DATABASE_URL` may point at SQLite (local dev — see `tasklytics.db`) or Postgres; `app/database.py` branches on the URL scheme. In Docker, the Postgres host must be `db` (the Compose service name), not `localhost`, and the user/password/dbname must match the `db` service's own env in `docker-compose.yml`. `ENV=docker` skips loading `.env` via `python-dotenv` (Docker injects env vars directly).

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
- `src/pages/` — routed views (`Login`, `Register`, `Dashboard`). `Dashboard` composes `CreateTask`, `Analytics`, `AIInsights`, `ChatContainer`, `TaskList` (in that render order).
- `src/components/chat/` — `ChatContainer` (holds message state, calls the `/chat` endpoint), `ChatMessages`, `ChatInput`. Separate from `AIInsights`, which hits the legacy `app/ai/` single-shot endpoint — don't conflate the two AI surfaces on the frontend either.

## Production Monitoring

External uptime monitoring via UptimeRobot (free tier), watching the live deployment at `https://tasklytics2ai.com`. Two independent monitors rather than one combined check — a failure in only one immediately narrows down which layer broke, without needing to check container logs first.

### Monitors

1. **Public Website Monitor**
   - Type: HTTP(S)
   - Target: `https://tasklytics2ai.com/`
   - Detects: DNS resolution, TLS handshake, `nginx` availability, and the frontend container being reachable — the baseline "is the site up at all" check.

2. **Backend Health Monitor**
   - Type: Keyword monitor (deliberately not a plain status-code check — see below)
   - Target: `https://tasklytics2ai.com/api/health`
   - Keyword: `"status":"ok"` (exact string, no space after the colon — matches FastAPI's default JSON serialization of the `/health` route)
   - Alert condition: keyword missing from the response
   - Detects: backend process and database connectivity specifically, independent of whether the frontend/nginx are still reachable.

### Why the backend monitor uses a keyword, not a status code

`app/main.py`'s `/health` route returns HTTP `200` in **both** its success and failure branches — the `except` branch returns `{"status": "error", ...}` but never overrides the status code. A plain "check for HTTP 200" monitor would therefore never detect a database outage through this endpoint, since it always answers `200` regardless of the database state. The keyword check on `"status":"ok"` is what actually distinguishes a healthy response from a degraded one — this is a real, verified property of the route's current implementation, not a hypothetical.

### Failure interpretation

| Symptom | Meaning |
|---|---|
| Public monitor DOWN (connection timeout) | `nginx` itself is unreachable — check `tasklytics_nginx`'s container status first, not the backend |
| Public monitor UP, health monitor DOWN (keyword missing) | `nginx` and the frontend are fine; the backend process is down or its database connection is broken — check `docker logs tasklytics_backend` and `docker exec tasklytics_db pg_isready` |
| Both monitors UP | No detected issue at the infrastructure layer this monitoring covers — does not prove every application feature works (e.g., the AI endpoints are outside its scope) |

Both failure modes were deliberately tested by stopping the relevant container (`tasklytics_nginx`, then `tasklytics_backend`) and confirming the expected monitor and alert fired, then confirming a separate recovery alert on restart.

### Architecture flow

```
UptimeRobot (external)
        |
        | HTTPS request every 5 min
        v
https://tasklytics2ai.com
        |
        v
   nginx (tasklytics_nginx)  <── [Public monitor checks this hop
        |                         + everything reachable below it]
        +--> frontend (SPA)
        |
        +--> /api/health --> backend (tasklytics_backend) --> PostgreSQL
                                    ^
                   [Backend monitor specifically checks this path,
                    including the DB connectivity check inside /health]
```

### Free-tier limitations

- No SSL certificate expiry monitoring — Let's Encrypt renewal is automated (webroot method, verified via `certbot renew --dry-run`), but there is no external tripwire if renewal silently fails. Would need a paid tier or a separate mechanism to close this gap.
- No monitor grouping — the two monitors are independent dashboard entries, not organized under a shared project/tag.
- Limited monitor name customization.

## Notes

- `.claude/CLAUDE.md` (auto-loaded alongside this file) covers the project's tech stack summary, general dev principles, and PR/git standards — this file is the map of how the code actually fits together.
- `.claude/skills/pr-description/` implements the PR-description skill those standards reference.
