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

**Status: configured and verified.** External uptime monitoring via UptimeRobot (free tier), two independent monitors — a failure in only one narrows down which layer broke without checking logs first.

| Monitor | Type | Target | Detects |
|---|---|---|---|
| Public Website | HTTP(S) | `https://tasklytics2ai.com/` | DNS, TLS handshake, nginx, frontend reachability |
| Backend Health | **Keyword** | `https://tasklytics2ai.com/api/health` | Backend process + database connectivity specifically |

**Why the backend monitor uses a keyword, not a status code:** `/health` (`app/main.py`) returns HTTP `200` in **both** its success and failure branches — the `except` branch returns `{"status": "error", ...}` but never overrides the status code. A plain "check for 200" monitor would never detect a database outage through this endpoint. The keyword `"status":"ok"` (exact string, no space after the colon — matches FastAPI's default JSON serialization) is what actually distinguishes healthy from degraded.

**Verified by deliberate failure injection**, not assumed: stopped `tasklytics_nginx` → Public monitor went DOWN (connection timeout) → alert received. Stopped `tasklytics_backend` → Health monitor went DOWN (keyword missing) → alert received. Restarted both → recovery alerts received for each. This is the actual proof the monitors detect what they're meant to.

### Alerting configuration — reducing noise without losing signal

**Consecutive-failure threshold (the single highest-leverage noise control on free tier):** set each monitor to alert only after **2 consecutive failed checks**, not the first. A lone failed check is frequently a transient network blip between UptimeRobot's checking infrastructure and the VPS, not a real outage — alerting on check #1 trains you to ignore alerts; requiring 2 in a row (≈10 minutes at a 5-minute interval) filters that out while still catching anything that's actually down.

**One alert contact, not several overlapping ones:** a single email contact applied to both monitors. Adding redundant contacts (e.g., a personal email *and* a team alias both wired to the same monitor) is how duplicate alerts happen — one incident, multiple pings, and eventually someone starts ignoring one of the channels.

**Notify on both directions:** enable Down *and* Up (recovery) per monitor. Without the recovery alert, "is it still broken?" becomes a manual check instead of a notification — you want to be told the incident ended, not just that it started.

**Pause during planned maintenance:** before any deploy that recreates containers (`docker compose down` / `up -d --build`), pause both monitors, then unpause once verification (below) passes. A self-inflicted alert during a routine deploy is exactly the kind of noise that erodes trust in the alerting system — treat a paused monitor as a deliberate, logged action, not something to forget to re-enable.

**Slack / mobile, free-tier aware:** UptimeRobot's own mobile app supports push notifications on the free tier. For Slack specifically, check your dashboard's current alert-contact options before assuming a specific integration is free vs. paid — tier features change over time and this should be confirmed live rather than assumed stale from documentation. A **Webhook** alert contact (commonly available on free tier) pointed at a Slack Incoming Webhook URL is the usual no-paid-tier path if a native Slack integration isn't available on your plan.

### Verifying alerting changes actually work

Any time an alert setting changes (threshold, contact, pause behavior), re-run the same deliberate-failure test used to originally verify the monitors — stop the relevant container, confirm the alert behaves as newly configured (e.g., confirm it does *not* fire on the first failed check if the threshold was just raised to 2), restart, confirm recovery. A settings change that hasn't been re-verified is a claim, not a fact — same standard as everything else in this runbook.

### Severity levels

Mapped directly to the two real monitors, not an abstract scheme:

| Severity | Trigger | User impact | Response |
|---|---|---|---|
| **SEV1 — Critical** | Public Website monitor DOWN | Total outage — nobody can reach the site | Immediate; start Incident Response §1 now |
| **SEV2 — Degraded** | Backend Health monitor DOWN, Public Website still UP | Site loads, but login/tasks/AI are broken — often worse for trust than a clean outage, since it looks buggy rather than down for maintenance | Immediate; start at Incident Response Scenario B or C directly (Public monitor being UP already rules out Scenario A) |
| **SEV3 — Minor, non-alerting** | SSL cert inside its renewal window but not yet failed; a single transient AI request failure (Claude/Together) | None visible yet, or isolated to one request | No UptimeRobot alert exists for these today — SSL expiry has no monitor (free-tier gap, see "Free-tier limitations"); AI request failures belong in Sentry once `SENTRY_DSN` is set, not in uptime monitoring, since the app itself is still "up" |

### What should trigger an alert vs. not

**Should alert (wired to UptimeRobot today):**
- Public site unreachable for 2+ consecutive checks
- `/api/health` missing the `"status":"ok"` keyword for 2+ consecutive checks

**Should not alert as a production incident (by design):**
- A single failed AI request — transient upstream API errors are expected occasionally; this is an error-tracking concern (Sentry), not an uptime concern. Alerting on every individual failed AI call would be exactly the kind of noise this runbook's alerting section exists to avoid.
- `401`/`403`/`422` responses to bad input (wrong password, malformed request) — expected application behavior, not an incident.
- A failed CI run (`.github/workflows/backend-tests.yml`) — a pre-deploy signal in GitHub, not a live production alert; conflating the two channels would make it harder to tell "code doesn't pass tests" from "production is down."

### Escalation logic (solo developer)

No team to hand off to, so escalation here means **escalating your own response intensity and decision threshold over time** — not escalating to another person:

- **0–10 min from alert:** quick diagnostic pass — Incident Response §1–2 below (`docker compose ps`, targeted logs, obvious restart). Most incidents resolve at this tier.
- **10–30 min, still unresolved:** stop making incremental guesses. Check whether the last deploy correlates with the incident start (`git log -1 --format=%cd`), consider a full `docker compose down && up -d` recreate rather than continuing to poke at one container.
- **30+ min unresolved, or any sign of data corruption:** stop touching production. Take a fresh backup of the current (possibly degraded) state before doing anything further — including anything destructive-looking — then restore from the last known-good backup into a **new** database name to confirm it's good, per "Backup & restore" above, before considering promoting it. Under time pressure, memory of "what have I already tried" is unreliable — write it down as you go, not after.
- **Recurrence rule:** the same incident happening 2+ times in a rolling 7 days is itself an escalation trigger, independent of how fast any single instance was resolved — stop re-applying the same quick fix and schedule dedicated time for root-cause investigation instead. An undocumented incident tends to repeat.

## Incident Response

Detect → diagnose → recover → verify, for the three failure categories UptimeRobot's monitors can surface. Commands here are pointers into "Debugging workflow" above, not duplicated — this section is the decision flow for *which* command to run first, not a second copy of the commands themselves.

### 1. Detection

An incident starts with one of:
- UptimeRobot alert email (Public Website or Backend Health monitor DOWN)
- A user report
- Manual observation

First action, always: `docker compose ps` — before diagnosing anything, know which containers are actually `Up` vs. `Restarting`/exited. This alone often answers "which of the three scenarios below applies" in one command.

### 2. Diagnosis by scenario

**Scenario A — Site down (Public Website monitor DOWN, connection timeout)**

Meaning: nginx itself is unreachable — this is the outermost layer, so start there, not with the backend.
```bash
docker compose ps                    # is tasklytics_nginx Up?
docker logs --tail 50 tasklytics_nginx
docker exec tasklytics_nginx nginx -t
```
- Container not `Up` → it crashed or was stopped; see Recovery §3a.
- Container `Up` but still unreachable externally → check the VPS firewall (`sudo ufw status`) hasn't changed, and that DNS still resolves to the right IP (`dig tasklytics2ai.com`) — this is an infrastructure-layer problem, not a container problem.

**Scenario B — Backend failure (Backend Health monitor DOWN, keyword `"status":"ok"` missing)**

Meaning: nginx and the frontend are fine (Public monitor still UP); the backend process is down, or it's up but its database check inside `/health` is failing.
```bash
docker compose ps                    # is tasklytics_backend Up?
docker logs --tail 50 tasklytics_backend
docker logs -f tasklytics_backend    # live, if you can reproduce the failure
curl -s https://tasklytics2ai.com/api/health   # read the actual JSON — "database":"disconnected" narrows straight to Scenario C
```
- Container not `Up` / crash-looping → check the traceback in the logs; common causes already documented: missing/invalid `ANTHROPIC_API_KEY` (crashes at import, not just at request time), missing `SECRET_KEY`.
- Container `Up`, `/health` responds but with `"database":"disconnected"` → this **is** Scenario C, go there directly.

**Scenario C — Database failure (`/health` reports `"database":"disconnected"`, or `pg_isready` fails)**

```bash
docker compose ps                    # is tasklytics_db Up?
docker exec tasklytics_db pg_isready -U postgres -d tasklytics
docker logs --tail 50 tasklytics_db
```
- Container not `Up` → see Recovery §3c. Check `docker volume ls` / `docker volume inspect postgres_data` still exists before restarting — this is the one scenario where you should pause and confirm the volume is intact before touching anything, since it holds the only copy of production data outside of backups.
- Container `Up`, `pg_isready` succeeds, but the backend still reports disconnected → mismatch between `DATABASE_URL` (in `.env.docker`) and the `db` service's actual `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` (in the root `.env`) — a credential drift issue, not a database-down issue. Compare both files directly rather than guessing.

### 3. Recovery

**3a — nginx down:**
```bash
docker compose up -d nginx
docker logs --tail 20 tasklytics_nginx    # confirm clean startup, no repeated crash
```

**3b — backend down (config/code issue, not a crash loop from bad env):**
```bash
docker compose up -d backend
```
If it's crash-looping on a config problem (missing env var), fix `.env.docker` first, then:
```bash
docker compose up -d backend
```

**3c — database down:**
```bash
docker compose up -d db
docker exec tasklytics_db pg_isready -U postgres -d tasklytics
```
If the container won't start at all and logs show data corruption (not just "was stopped") — **do not** delete and recreate the volume as a first response. Restore from the most recent backup instead (see "Backup & restore" above), into a **new** database name first to confirm the backup is good, before touching production data.

**General-purpose recovery, when a targeted restart doesn't resolve it:**
```bash
docker compose down
docker compose up -d
```
`down` without `-v` does not touch the `postgres_data` volume — safe to use, but recreates all four containers, so expect a brief full outage rather than a single-service blip.

### 4. Verification after recovery

Don't close the incident on "the container shows `Up`" alone — confirm functionally:
```bash
curl -s https://tasklytics2ai.com/api/health          # expect {"status":"ok",...,"database":"connected"}
curl -I https://tasklytics2ai.com/                    # expect 200
```
Then check both UptimeRobot monitors show **Up** in the dashboard, and confirm the recovery email actually arrived — a monitor showing "Up" without a corresponding recovery notification having fired is itself worth investigating (could mean the alert contact silently broke).

Finally: if the incident required a code or config change (not just a restart), write down what happened and why in this file's "Open items" section or a dedicated postmortem note — an incident that isn't documented tends to repeat.

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

- [x] Uptime monitoring — configured, both monitors verified via deliberate failure injection with real alerts received (see "Monitoring & alerting" above)
- [x] Off-server backup storage (DigitalOcean Spaces bucket, rclone remote `tasklytics-spaces`) — created and manually verified: `backup-sync.sh` run confirmed remote file count matching local
- [ ] Off-server backup **automation** — the sync above was a one-time manual run; `crontab -l` needs the `backup-sync.sh` entry added (documented above under "Off-server backup setup") for this to protect data going forward, not just prove the mechanism works once
- [ ] UptimeRobot alert threshold — recommended 2-consecutive-failure setting (documented above under "Alerting configuration") needs to actually be applied per monitor in the dashboard, then re-verified with a deliberate-failure test
- [ ] Sentry `SENTRY_DSN` — scaffold is in place and verified inert/functional in both directions (`app/main.py`), but no real project/DSN has been created
- [ ] Frontend JWT silent-refresh integration (`AuthContext.jsx`/`api/api.js`) — backend `/auth/refresh` is implemented and tested, frontend wiring is not
- [ ] A real run of `tests/ai_eval/run_eval.py` against the live Claude API — the framework is built and its assertion logic is verified against synthetic data, but never run against a real response
- [ ] 4 pre-existing frontend lint errors (`TaskList.jsx`, `AuthContext.jsx`, `Register.jsx`) — unrelated to Phase 5, left untouched as out of scope, CI's lint step is report-only because of this
