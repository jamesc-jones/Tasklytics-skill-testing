# Tasklytics Production Runbook

Operational reference for the live deployment at https://tasklytics2ai.com.

## Architecture

```
Internet
   |
   v
nginx (Docker, tasklytics_nginx) — TLS termination, rate limiting, security headers
   |
   +--> React frontend (tasklytics_frontend, serve -s dist, port 3000 internal)
   |
   +--> FastAPI backend (tasklytics_backend, uvicorn, port 8000 internal)
             |
             +--> PostgreSQL (tasklytics_db, port 5432 internal)
             |
             +--> Claude API (via anthropic SDK, services/ai/claude_client.py)
             +--> Together AI (legacy /ai/task-insights path, app/ai/client.py)
```

- VPS: DigitalOcean, Ubuntu 24.04, non-root operational user `deploy`
- Repo location on VPS: `/var/www/Tasklytics-skill-testing`
- Only `nginx` publishes host ports (80, 443); backend/frontend/db are reachable only over the internal Compose network
- Certificate: Let's Encrypt, webroot-authenticated renewal (`/etc/letsencrypt/live/tasklytics2ai.com/`)

## Service reference

| Container | Role | Healthcheck |
|---|---|---|
| `tasklytics_nginx` | Reverse proxy, TLS | `curl -k -f https://localhost/` |
| `tasklytics_frontend` | Static React build (`serve -s dist`) | Node `http.get` on :3000 |
| `tasklytics_backend` | FastAPI/uvicorn | Python `urllib` GET on :8000 |
| `tasklytics_db` | PostgreSQL 15 | `pg_isready` |

All four run `restart: always` and have `logging: max-size 10m, max-file 3` (30MB cap per container).

## Deployment / update procedure

```bash
cd /var/www/Tasklytics-skill-testing
git pull

# If only docker-compose.yml or nginx/default.conf changed (no Dockerfile changes):
docker compose up -d

# If either Dockerfile changed:
docker compose build backend frontend
docker compose up -d backend frontend
```
Never `docker compose down -v` / `docker volume rm` on this stack without explicit intent — `-v` destroys the `postgres_data` named volume.

## Debugging workflow

**nginx:**
```bash
docker logs --tail 50 tasklytics_nginx
docker logs tasklytics_nginx 2>&1 | grep -E "\[error\]|\[warn\]|\[emerg\]"
docker exec tasklytics_nginx nginx -t
```

**Backend:**
```bash
docker logs --tail 50 tasklytics_backend
docker logs -f tasklytics_backend          # live, while reproducing an issue
docker exec tasklytics_backend printenv | grep -v -E "PASSWORD|API_KEY|SECRET"
```

**Database:**
```bash
docker exec tasklytics_db pg_isready -U postgres -d tasklytics
docker logs --tail 50 tasklytics_db        # startup/errors only — query-level logging is off by default
docker exec -it tasklytics_db psql -U postgres -d tasklytics -c "\dt"
```

**Tracing one request end-to-end (browser → nginx → FastAPI → database → Claude API):**
1. `docker compose logs -f --tail 20` in one terminal (all four services, interleaved by timestamp).
2. Reproduce the action in the browser.
3. Read top to bottom:
   - No nginx access line at all → request never left the browser, or DNS/firewall issue, not an app problem.
   - nginx line present, no backend line → break is between those two containers (proxy/network), not the app logic.
   - Backend line present, then a traceback → identify by exception type: `anthropic.AuthenticationError` → bad/missing `ANTHROPIC_API_KEY`; error inside `response_parser.py` → Claude returned a reply the parser didn't expect (e.g., wrapped in a markdown fence); a SQLAlchemy/psycopg error → database connectivity, cross-check `DATABASE_URL` against the `db` service's actual credentials.
   - Clean `200` at every layer → not a backend issue; re-check the frontend's handling of the response.

## Backup & restore

**Status: confirmed operational on the live VPS** (see `docs/PHASE_4_COMPLETION_REPORT.md`) — daily `pg_dump` cron, 30-day retention cleanup, and `cron.service` active, all confirmed via real command output. The manual commands below still work standalone; `scripts/` (repo root) now wraps the validation and restore steps so they don't need to be retyped by hand during an actual incident.

```bash
# Manual backup
docker exec tasklytics_db pg_dump -U postgres tasklytics > /var/backups/tasklytics/tasklytics_backup_$(date +%Y-%m-%d).sql

# Automated (cron) - confirmed present on the VPS
# 0 2 * * * docker exec tasklytics_db pg_dump -U postgres tasklytics > /var/backups/tasklytics/tasklytics_backup_$(date +\%Y-\%m-\%d).sql
# 0 3 * * * find /var/backups/tasklytics -type f -mtime +30 -delete

# Validate today's backup actually ran and is non-empty/recent
./scripts/validate-backup.sh /var/backups/tasklytics 25
# Consider adding to cron a few minutes after the 2am dump:
# 0 5 * * * /path/to/repo/scripts/validate-backup.sh || mail -s "Tasklytics backup validation failed" you@example.com

# Restore into a throwaway database (never directly into production)
./scripts/restore-backup.sh /var/backups/tasklytics/tasklytics_backup_YYYY-MM-DD.sql tasklytics_restore_test
# Review the reported counts, then drop when done (the script prints the exact command)
```

Both scripts were verified against real Postgres containers and real dump files before being committed (not just syntax-checked) — see `docs/PHASE_5_EXECUTION_TRACKER.md` item 5A.1 for the specific test cases and results.

### Off-server backup setup (manual — requires an external account)

Backups currently exist only on the same VPS disk as the data they protect — a real, documented residual risk. `scripts/backup-sync.sh` wraps the sync step, but it requires an object storage account that can't be created without you:

1. Create a DigitalOcean Spaces bucket (or any S3-compatible object storage) — DigitalOcean Control Panel → Spaces → Create Space.
2. Generate a Spaces API key (Control Panel → API → Spaces Keys).
3. Install `rclone` on the VPS: `sudo apt install -y rclone`.
4. Configure the remote: `rclone config` → New remote → type `s3` → provider `DigitalOcean Spaces` → paste the key/secret from step 2.
5. Test: `./scripts/backup-sync.sh /var/backups/tasklytics spaces:your-bucket-name` — should report matching local/remote file counts.
6. Add to cron, after the nightly dump: `30 2 * * * /path/to/repo/scripts/backup-sync.sh /var/backups/tasklytics spaces:your-bucket-name`

Not performed as part of this work — no account was created, per the constraint on this pass. This is genuinely blocked on a human action, not a shortcut.

## Monitoring & alerting

**Status: not yet configured** — no automated uptime monitoring exists today; health verification has only ever happened via manual `curl` during deployment sessions. No external monitoring account was created as part of this work, per the "no external accounts" constraint — documenting the exact manual setup instead.

**Health check target:** the backend has no dedicated `/health` route — the root endpoint doubles as one:
```
GET https://tasklytics2ai.com/api/
Expected: 200, body {"message":"Tasklytics Backend API running!"}
```
This proves nginx→backend routing works. It does **not** touch the database — for a deeper check, see `PRODUCTION_RUNBOOK.md`'s "Tracing one request end-to-end" section above, which uses a login attempt against `/api/auth/login` as an indirect database-connectivity check.

### Manual setup (external account required)

1. Create a free account at an uptime-monitoring service (e.g., UptimeRobot).
2. Add an HTTP(S) monitor:
   - URL: `https://tasklytics2ai.com/api/`
   - Expected status: `200`
   - Interval: 5 minutes (free-tier typical minimum)
   - Alert contact: email (and SMS if the plan supports it)
3. Verify the monitor actually works before trusting it: stop `tasklytics_nginx` (`docker compose stop nginx`), confirm an alert fires within the configured interval, then `docker compose start nginx` and confirm a recovery notification also fires.

Not performed here — genuinely requires an account only you can create.

## Security posture (as last verified in-conversation, not re-confirmed today)

- UFW: 22/80/443 allowed, default deny incoming
- SSH: key-only, root login disabled, `deploy` user only
- Fail2Ban: `sshd` jail active
- HTTPS: Let's Encrypt, HTTP→HTTPS redirect, `.env`/`.git` blocked at nginx (`403`, confirmed via `curl`)
- Containers: backend runs as `appuser`, frontend as `node` (non-root)
- Secrets: `.env`/`.env.docker` gitignored; `docker-compose.yml`'s `db` service reads `POSTGRES_*` from a gitignored root `.env` rather than a literal value
- Known residual: the original leaked Postgres password remains in git history (rotated live, not purged from history — accepted tradeoff, documented decision)

## Open items

The five items below (`ANTHROPIC_API_KEY` presence, backup cron status, `/api/chat` and `/api/ai/task-insights` production tests, live log rotation, `daemon.json` presence) were all resolved with real command output — see `docs/PHASE_4_COMPLETION_REPORT.md`. Current open items, from Phase 5:

- [ ] Uptime monitoring account creation and setup (documented above, blocked on human action)
- [ ] Off-server backup storage account creation and setup (documented above, blocked on human action)
- [ ] Sentry `SENTRY_DSN` — scaffold is in place and verified inert/functional in both directions (`app/main.py`), but no real project/DSN has been created
- [ ] Frontend JWT silent-refresh integration (`AuthContext.jsx`/`api/api.js`) — backend `/auth/refresh` is implemented and tested, frontend wiring is not
- [ ] A real run of `tests/ai_eval/run_eval.py` against the live Claude API — the framework is built and its assertion logic is verified against synthetic data, but never run against a real response
- [ ] 4 pre-existing frontend lint errors (`TaskList.jsx`, `AuthContext.jsx`, `Register.jsx`) — unrelated to Phase 5, left untouched as out of scope, CI's lint step is report-only because of this
