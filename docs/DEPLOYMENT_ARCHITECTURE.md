# Deployment Architecture — Tasklytics

System design reference. All claims below are traceable to repository source, `docker-compose.yml`, `nginx/default.conf`, or `CLAUDE.md`; no claim in this document describes production runtime behavior that hasn't been separately verified (see `PRODUCTION_VERIFICATION.md` for that distinction).

## High-level architecture

```
                              User
                               |
                             HTTPS
                               |
                    NGINX Reverse Proxy (Docker)
                     - TLS termination
                     - HTTP -> HTTPS redirect
                     - Rate limiting (/api/)
                     - Security headers
                     - .env / .git blocking
                               |
                +--------------+--------------+
                |                             |
           Frontend                       Backend
        React 19 + Vite                  FastAPI
        (served via `serve`,                |
         static build)              JWT Authentication
                                             |
                                    AI Agent Layer
                                     (ChatAgent)
                                             |
                          +------------------+------------------+
                          |                                     |
                    Task Tools                       Productivity Analysis
                 (get_tasks, DB query)          (get_productivity_stats)
                          |                                     |
                          +------------------+------------------+
                                             |
                                  Context Engineering Layer
                                     (build_task_context)
                                             |
                                     Claude API (Anthropic SDK)
                                             |
                                  Structured Output Parser
                                    (JSON response)

                                    Backend also connects to:
                                    PostgreSQL 15 (User, Task tables)
```

Note: the legacy `/ai/task-insights` endpoint (Together AI-backed) bypasses the AI Agent Layer entirely — it is a separate, older code path. See "AI Architecture" below.

## Frontend

- **React 19 + Vite**, plain JavaScript/JSX (no TypeScript) — confirmed via `package.json` and file extensions throughout `src/`
- **API communication:** `src/api/` — one file per backend resource (`api.js`, `ai.js`, `analytics.js`), built on plain `fetch` (not an axios instance, despite axios being a dependency); the JWT is passed explicitly per-call rather than attached via a global interceptor
- **Base URL resolution:** `src/api/config.js` hardcodes `isDev ? "http://localhost:8000" : "/api"` — a commented-out `VITE_API_URL` env-based version exists in source but is currently dead code; the production build always resolves to the relative path `/api`, which nginx proxies to the backend with the `/api` prefix stripped
- **State:** JWT held in React state + `localStorage` (`src/context/AuthContext.jsx`); a token-reload-on-mount effect exists in source but is currently commented out
- **Chat UI:** `src/components/chat/` (`ChatContainer`, `ChatMessages`, `ChatInput`) — calls `/chat`, distinct from the older `AIInsights` component, which calls the legacy `/ai/task-insights` endpoint

## Backend

- **FastAPI**, Python 3.11
- **SQLAlchemy** for the ORM layer; **Alembic** for migrations (`alembic/versions/`) — note `app/main.py` also calls `Base.metadata.create_all(bind=engine)` on every startup, so schema drift between models and applied migrations can go unnoticed in environments that don't rely solely on `alembic upgrade head`
- **JWT authentication:** `python-jose`, HS256, signed with `SECRET_KEY`. Issued on login/register (`app/routes/auth.py`); verified per-request via `get_current_user` (`app/auth/auth_dependencies.py`), which decodes the token and loads the `User` by id. `require_admin` wraps this to gate admin-only routes on `role == "admin"`.
- **Routing note:** `app/routes/tasks.py` and `app/routes/analytics.py` both define `GET /tasks/analytics`. Because `tasks.router` is registered first in `app/main.py`, its handler (correctly filtering by `Task.user_id`) always wins; `analytics.py`'s handler (which references a non-existent `Task.owner_id` field) is dead code, unreachable in normal operation.

## Database

- **PostgreSQL 15** in production (Docker), SQLite supported for local dev (`app/database.py` branches on the `DATABASE_URL` scheme)
- **Schema:** two tables, `User` and `Task`, one-to-many via `Task.user_id`. Every task route filters by `user_id` for regular users; the filter is skipped for `role == "admin"`.
- **Credentials:** consumed via `${POSTGRES_USER}` / `${POSTGRES_PASSWORD}` / `${POSTGRES_DB}` substitution in `docker-compose.yml`, sourced from a gitignored root `.env` (not a literal value in the tracked file)

## AI Architecture

Two independently-evolved subsystems exist side by side — confirmed both from `CLAUDE.md` and from git history (e.g. `abff6cb Refactor chatbot into Claude agent architecture layer`, `ba330a0 Working on adding Claude Agent SDK`), which shows the current system was built as a later addition rather than a rewrite of the legacy one.

### Legacy: `app/ai/` — single-shot insights
- `POST /ai/task-insights`
- `app/ai/client.py:call_llm` calls **Together AI** directly via `requests` (model `openai/gpt-oss-20b`, `TOGETHER_API_KEY`)
- Prompt built in `app/ai/prompts.py`
- Still live and reachable; still used by the frontend's `AIInsights` component

### Current: `app/ai_agents/` + `app/services/ai/` — chat-based agent
- `POST /chat`, routed through `app/api/routes/chat.py` -> `ChatAgent.run()`
- **Tool usage:** `ChatAgent.run()` calls two explicitly-labeled "tools" in source (`app/ai_agents/tools.py`): `get_tasks` (queries the user's tasks from Postgres) and `get_productivity_stats` (computes completion rate from those tasks) — this is a lightweight, hand-rolled tool-calling pattern, not the Anthropic SDK's native tool-use feature
- **Context building:** `build_task_context` (`app/services/ai/context_builder.py`) assembles the tool outputs into the context object passed to Claude
- **Claude call:** `services/ai/claude_client.py` — constructs `anthropic.Anthropic()` at **module import time** (meaning a missing/invalid `ANTHROPIC_API_KEY` prevents the entire backend from starting, not just this endpoint from working), hardcoded model `claude-sonnet-4-5`
- **Structured responses:** the prompt explicitly demands raw JSON with no markdown fences; `services/ai/response_parser.py` parses the reply into the `ChatResponse` schema (`app/models/chat_models.py`: `response`, `priority_tasks`, `insight`). The parser currently only strips a leading ` ```json ` fence — if the prompt is ever edited in a way that changes Claude's formatting tendency, the parser's stripping logic needs to stay in sync.
- An additional file, `app/ai_agents/insight_agent.py`, exists in the codebase but is **not imported or referenced anywhere else** (confirmed via repository-wide search) — appears to be unused/in-progress code, not part of the active request path.

## Infrastructure

- **Docker Compose**, four services (`nginx`, `frontend`, `backend`, `db`), one `docker-compose.yml` at the repository root
- **NGINX reverse proxy** — the only service exposing host ports (`80`, `443`); `frontend`/`backend`/`db` use `expose` only, reachable exclusively over the internal Compose network
- **HTTPS** — Let's Encrypt certificate mounted read-only (`/etc/letsencrypt:/etc/letsencrypt:ro`) into the nginx container; HTTP server block redirects to HTTPS
- **Certbot** — runs on the host (not in Docker), webroot-authenticated (switched from `--standalone` specifically because the containerized nginx already owns port 80, so `--standalone`'s own port-80 binding during renewal conflicted with it)
- **Health checks** — per-service, protocol-appropriate probes (HTTP GET for backend/frontend, `pg_isready` for Postgres, HTTPS `curl` for nginx), added specifically to close the gap where `restart: always` only reacts to a process exiting, not to a process that is running but non-functional
- **Logging** — `json-file` driver, `max-size: 10m` / `max-file: 3` per service, added specifically because the Docker default has no size cap and none was previously configured

## Architectural decisions and tradeoffs

**Why Docker Compose (rather than Kubernetes or a managed PaaS)?** The deployment is a single VPS running four tightly-coupled services with no need for multi-node orchestration, autoscaling, or rolling updates across replicas. Compose gives the full stack a single declarative file, co-located secrets/volume/network config, and a low operational surface area appropriate for this scale — the tradeoff is that scaling beyond one host, or achieving zero-downtime deploys, would require migrating to something else later.

**Why nginx as the reverse proxy?** A single entry point lets TLS termination, rate limiting, security headers, and static-file/API routing live in one well-understood, heavily-documented layer, rather than duplicating that logic inside FastAPI or the frontend server. It also means only one container needs to publish host ports — backend/frontend/db stay off the public network entirely by construction, not by convention.

**Why JWT authentication (rather than server-side sessions)?** JWTs are stateless — the backend doesn't need a session store, which keeps the architecture simpler given there's no separate cache/session layer (like Redis) elsewhere in this stack. The tradeoff, inherent to JWTs generally, is that revoking a single issued token before its expiry isn't possible without adding a deny-list — not currently implemented here.

**Why structured (JSON) AI responses rather than freeform text?** The frontend's chat UI needs to render distinct fields (`response`, `priority_tasks`, `insight`) as separate UI elements, not a single blob of prose — structured output lets the frontend do that without its own parsing/NLP layer. The tradeoff is fragility: the current parser only handles one specific deviation (a leading ` ```json ` fence), so any other formatting drift from Claude would break parsing rather than degrading gracefully.

**Why keep the legacy AI system running alongside the current one, instead of removing it?** Git history shows the current chat-based system was added later as a distinct architectural layer, not a refactor of the original. The frontend's `AIInsights` component still depends on the legacy endpoint, so removing `app/ai/` would be a breaking frontend change, not a pure cleanup — this looks like an intentional (or at least accepted) incremental-migration state rather than an oversight, but nothing in the repository documents a plan to formally deprecate or remove the legacy path.
