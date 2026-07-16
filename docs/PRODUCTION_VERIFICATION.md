# Production Verification Checklist — Tasklytics

Evidence-based verification record. Each item is marked Verified (with source), Reported (stated in session, not independently re-confirmed), or Not Verified.

## 1. Container Verification

| Container | Restart policy | Healthcheck | Status |
|---|---|---|---|
| `tasklytics_backend` | `always` (docker-compose.yml) | Python `urllib` GET on `:8000` | **Reported** healthy via `docker compose ps` |
| `tasklytics_frontend` | `always` (docker-compose.yml) | Node `http.get` on `:3000` | **Reported** healthy via `docker compose ps` |
| `tasklytics_db` | `always` (docker-compose.yml) | `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}` | **Reported** healthy; `pg_isready` output separately reported as "accepting connections" |
| `tasklytics_nginx` | `always` (docker-compose.yml) | `curl -k -f https://localhost/` | **Reported** healthy |

Healthcheck definitions themselves are **Verified** directly from `docker-compose.yml`. The four backend/frontend healthcheck commands were also independently tested against locally-built images outside of this repo's CI (built and run via `docker build`/`docker run`, healthcheck command executed manually inside each, all four exited `0`) — this confirms the commands are *correct*, not that the live production containers are currently passing them (that part is Reported only).

## 2. Environment Verification

**Required environment variables** — confirmed from `tasklytics-skill-testing-backend/.env.docker.example` and source references:

| Variable | Required for | Source |
|---|---|---|
| `DATABASE_URL` | App startup, all DB access | `app/database.py` |
| `SECRET_KEY` | JWT signing | `app/auth/auth_dependencies.py` |
| `ENV` | Controls `.env` loading behavior | `app/main.py` |
| `ANTHROPIC_API_KEY` | **Hard requirement** — constructed at module import time; missing/invalid value prevents the backend from starting at all | `app/services/ai/claude_client.py` |
| `TOGETHER_API_KEY` | Legacy `/ai/task-insights` endpoint only; does not block startup if missing | `app/ai/client.py` |
| `VOYAGE_API_KEY` | Declared as an expected var; **not referenced anywhere in current source** (confirmed via repository-wide search) | — |
| `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` | Root `.env`, consumed by `docker-compose.yml`'s `db` service | `docker-compose.yml` |

**Secrets management approach** — Verified from repository state:
- `.env`, `.env.docker`, `.env.production` (backend) and `.env` (frontend) are gitignored; only `.env.docker.example` (a template with placeholder values) is tracked
- Root `.env` (Postgres credentials) is gitignored as of commit `0bbca9d`
- `docker-compose.yml`'s `db` service reads `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` via `${VAR}` substitution rather than a literal value (commit `0bbca9d`)
- **Known residual, not remediated:** the git history for this repository contains two previously-real Postgres passwords in plaintext (predating the above fix). The live credential was rotated via `ALTER USER ... WITH PASSWORD` (reported, not independently re-confirmed) — the exposed values are treated as dead/expired, but git history has not been rewritten to remove them. This is a documented, accepted tradeoff, not an oversight.

## 3. Backup Verification

**Status: Disputed — not resolved.** Session records contain two directly contradictory claims:
- Claim A: daily `pg_dump` cron at `02:00`, retention cleanup (`find ... -mtime +30 -delete`) at `03:00`, `cron.service` active, and a restore test into a temporary database reporting `users = 1` / `tasks = 10` rows recovered.
- Claim B (later in the same deployment): "Automated backups NOT implemented yet."

Neither claim has been confirmed with raw `crontab -l` / `ls -la /var/backups/tasklytics/` output pasted into the session. **This item must be re-verified before it can be marked complete or incomplete.**

If confirmed present, expected configuration:
```
0 2 * * * docker exec tasklytics_db pg_dump -U postgres tasklytics > /var/backups/tasklytics/tasklytics_backup_$(date +\%Y-\%m-\%d).sql
0 3 * * * find /var/backups/tasklytics -type f -mtime +30 -delete
```
Backup location: `/var/backups/tasklytics/` (chosen deliberately outside any Docker-managed path, per `PRODUCTION_RUNBOOK.md`).

## 4. Logging Verification

**Configuration: Verified** directly from `docker-compose.yml` (commit `1d3d9ad`) — all four services:
```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```
Validated locally via `docker compose config` prior to commit, confirming correct YAML resolution (not merely correct-looking source).

**Live effect on production containers: Not Verified.** `docker inspect <container> --format '{{.HostConfig.LogConfig.Config}}'` has not been run against the actual VPS containers since this config was deployed. Expected result if applied: `map[max-file:3 max-size:10m]`.

**Host-level default (`/etc/docker/daemon.json`): Not Verified** — unknown whether a host-wide default also exists.

## 5. AI Endpoint Verification

**Authentication flow** (confirmed from source, `app/routes/auth.py` and `app/auth/auth_dependencies.py`):
```
User login (POST /api/auth/login)
        |
        v
JWT issued (HS256, python-jose, signed with SECRET_KEY)
        |
        v
Protected API request (Authorization: Bearer <token>)
        |
        v
Backend validation (get_current_user dependency — decodes token, loads User by id)
        |
        v
Claude processing (ChatAgent.run(), for /chat only)
```

**Endpoint status:**

| Endpoint | Schema confirmed from source | Production test status |
|---|---|---|
| `POST /api/auth/login` | `{"email": str, "password": str}` → `{"access_token", "token_type", "user"}` (`app/routes/auth.py`) | **Reported** working (used to obtain tokens for other tests earlier in this deployment) |
| `POST /api/chat` | `{"message": str}` → `{"response", "priority_tasks", "insight"}` (`app/models/chat_models.py`) | **Not Verified** — no status code or response body captured |
| `POST /api/ai/task-insights` | `{"tasks": [{"title", "completed", "priority", "due_date"}]}` → `{"success", "insight"}` (`app/ai/routes.py`) | **Not Verified** — no status code or response body captured |

## 6. Production Readiness Assessment

**Verified:**
- HTTPS, HTTP→HTTPS redirect, security headers, `.env`/`.git` blocking at nginx
- UFW firewall, SSH key-only auth with root login disabled, Fail2Ban active on SSH
- Non-root container execution for backend/frontend
- Docker healthcheck and log-rotation *configuration* (source-level)
- Basic infrastructure health (backend/frontend/db reachability, root API endpoint)

**Partially verified (configuration correct, live confirmation missing):**
- Log rotation actually applied to running containers
- Container health status at any given moment beyond what was reported at one point in time

**Not verified — should be resolved before this deployment is described as production-complete:**
- Backup automation (disputed status, unresolved)
- AI endpoint functionality in production (`/api/chat`, `/api/ai/task-insights`)
- `ANTHROPIC_API_KEY` validity in the live container
- Restore procedure has been tested once (reported); it has not been re-tested since the credential rotation or since the compose file's `db` service was reparameterized

**Recommended before declaring Phase 4 complete:** run the consolidated verification commands in `PRODUCTION_RUNBOOK.md` / requested repeatedly in-session, capture the raw output, and update this document's "Reported"/"Not Verified" items to "Verified" only where output actually confirms them.
