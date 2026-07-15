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

```bash
# Manual backup
docker exec tasklytics_db pg_dump -U postgres tasklytics > /var/backups/tasklytics/tasklytics_backup_$(date +%Y-%m-%d).sql

# Automated (cron)
# 0 2 * * * docker exec tasklytics_db pg_dump -U postgres tasklytics > /var/backups/tasklytics/tasklytics_backup_$(date +\%Y-\%m-\%d).sql
# 0 3 * * * find /var/backups/tasklytics -type f -mtime +30 -delete

# Restore test (into a throwaway database, never directly into production)
docker exec -it tasklytics_db psql -U postgres -c "CREATE DATABASE tasklytics_restore_test;"
docker exec -i tasklytics_db psql -U postgres -d tasklytics_restore_test < /var/backups/tasklytics/tasklytics_backup_YYYY-MM-DD.sql
docker exec -it tasklytics_db psql -U postgres -d tasklytics_restore_test -c "SELECT count(*) FROM users; SELECT count(*) FROM tasks;"
docker exec -it tasklytics_db psql -U postgres -c "DROP DATABASE tasklytics_restore_test;"
```
**Status as of this writing: unconfirmed on the live VPS** — prior conversation notes conflict on whether the cron entries are actually present. Run `crontab -l` and `ls -la /var/backups/tasklytics/` to confirm before relying on this.

## Security posture (as last verified in-conversation, not re-confirmed today)

- UFW: 22/80/443 allowed, default deny incoming
- SSH: key-only, root login disabled, `deploy` user only
- Fail2Ban: `sshd` jail active
- HTTPS: Let's Encrypt, HTTP→HTTPS redirect, `.env`/`.git` blocked at nginx (`403`, confirmed via `curl`)
- Containers: backend runs as `appuser`, frontend as `node` (non-root)
- Secrets: `.env`/`.env.docker` gitignored; `docker-compose.yml`'s `db` service reads `POSTGRES_*` from a gitignored root `.env` rather than a literal value
- Known residual: the original leaked Postgres password remains in git history (rotated live, not purged from history — accepted tradeoff, documented decision)

## Open items — not yet confirmed with real command output

- [ ] `ANTHROPIC_API_KEY` presence/format on the live container
- [ ] Automated backup cron entries actually present and running
- [ ] `/api/chat` and `/api/ai/task-insights` tested against production with a real token
- [ ] Log rotation (`max-size`/`max-file`) confirmed applied on the live containers post-deploy
- [ ] Whether `/etc/docker/daemon.json` also sets a host-level default (would be redundant with, not conflicting with, the per-service config)
