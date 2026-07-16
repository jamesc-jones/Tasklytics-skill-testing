# Phase 5 Execution Tracker — Tasklytics

Operational tracker for Phase 5 implementation. Same evidence standard as Phase 4: **a feature is not complete because code exists.** It is complete only when:

1. **Implemented** — code/config exists
2. **Tested** — exercised, not just written
3. **Verified** — real output captured proving it works (command output, not narrative)
4. **Documented** — recorded here and in the relevant doc, with the evidence attached

No item in this tracker moves to "Complete" without all four. This document itself contains no implementation — planning and tracking only, per instruction.

## Status legend

`Not Started` · `Decision Required` · `In Progress` · `Implemented (unverified)` · `Complete`

---

## Summary table

| Phase Item | Status | Current State | Implementation Evidence | Verification Evidence | Remaining Risks |
|---|---|---|---|---|---|
| **5A.1** Off-server database backups | Not Started | Local backups confirmed working (Phase 4): cron `0 2 * * *`/`0 3 * * *`, dated files present, `cron.service` active. No off-server copy exists. | — | — | Backup and primary data share one VPS disk until implemented |
| **5A.2** Uptime monitoring | Not Started | No automated monitoring exists; only manual `curl` checks during deployment sessions | — | — | Outages discovered reactively, not proactively |
| **5A.3** Error tracking | Not Started | No APM/error-tracking tool integrated; visibility limited to `docker logs tasklytics_backend` | — | — | Silent exceptions undetected without active manual log review |
| **5B.4** CI/CD pipeline | Not Started | `.github/workflows/` confirmed empty (direct listing); all deploys to date are manual `git pull` + `docker compose up` | — | — | No automated gate — a broken commit can be manually deployed with nothing to catch it |
| **5B.5** Dependency and Docker version pinning | Not Started | `nginx:latest` floating; `postgres:15` major-only; base images untagged-patch; backend `requirements.txt` fully pinned; frontend `package.json` uses `^` ranges | — | — | Non-reproducible builds; version drift possible on any future rebuild |
| **5C.6** JWT refresh token decision and implementation | Decision Required | `create_refresh_token()` exists in `auth_utils.py`, confirmed never called anywhere in source; access tokens are 15-minute-only | — | — | Code currently implies an unbuilt capability; inconsistent state until Option A/B is decided |
| **5C.7** Expanded automated testing | Not Started | Only `tests/routes/test_chat.py` exists; zero auth/task/admin backend tests; zero frontend tests | — | — | Item 4's CI has limited value until real coverage exists behind it |
| **5D.8** Claude usage tracking | Not Started | `claude_client.py` discards `response.usage`; no token/cost logging anywhere | — | — | No visibility into per-request cost or usage growth |
| **5D.9** Prompt versioning | Not Started | Prompt is an inline f-string in `claude_client.py`; no version identifier beyond git's file-level history | — | — | Blocks item 10 — can't compare prompt versions that were never labeled |
| **5D.10** AI evaluation framework | Not Started | No systematic evaluation exists; only ad hoc manual testing (Phase 4's `/chat` test confirmed response *shape*, not output *quality*) | — | — | Quality regressions from prompt/model changes are currently undetectable; depends on item 9 |

---

## Phase 5A — Reliability Foundation

### 1. Off-server database backups

- **Why this exists:** a backup's purpose is to survive failure of the primary system. A backup on the same disk as the data it protects doesn't satisfy that — VPS disk failure or loss destroys both together.
- **Current evidence from repository:** no repository evidence applies here (this is VPS-operational, not code) — current state is drawn from Phase 4's verified `crontab -l`/`ls -la /var/backups/tasklytics/` output, confirming local-only backups exist and run on schedule.
- **Definition of done:** (1) a sync mechanism (e.g., `rclone`) pushes backups to off-server storage on a schedule; (2) tested by triggering a real sync; (3) verified by listing the remote bucket *and* performing a full restore from the offsite copy specifically into a temporary database; (4) documented in `PRODUCTION_RUNBOOK.md` and `PRODUCTION_VERIFICATION.md`.
- **How success will be verified:** `rclone ls <remote>:<bucket>` output matching local file count/dates, plus a restored temporary database with row counts matching the source — both pasted as real command output, not summarized.

### 2. Uptime monitoring

- **Why this exists:** monitoring must not share a failure domain with what it monitors — an outage currently has no detection mechanism independent of a human checking.
- **Current evidence from repository:** none — no monitoring config exists in-repo or on the VPS.
- **Definition of done:** (1) external monitor configured against `https://tasklytics2ai.com/api/`; (2) tested by a deliberate outage; (3) verified by a real alert notification; (4) documented (monitor URL/config) in `PRODUCTION_RUNBOOK.md`.
- **How success will be verified:** stop `tasklytics_nginx`, confirm an alert arrives within the configured interval; restart, confirm a recovery notification arrives.

### 3. Error tracking

- **Why this exists:** exceptions are currently only visible via manual `docker logs` inspection — no passive detection mechanism exists.
- **Current evidence from repository:** confirmed absent — no error-tracking SDK in `requirements.txt`.
- **Definition of done:** (1) Sentry SDK initialized in `app/main.py` with `SENTRY_DSN` from env; (2) tested by deliberately triggering an exception; (3) verified by the exception appearing in the Sentry dashboard with a full stack trace; (4) documented (new env var) in `.env.docker.example`.
- **How success will be verified:** a screenshot or direct link to a real captured event in the Sentry dashboard, correlated to a specific, deliberately-triggered test exception.

---

## Phase 5B — Deployment Engineering

### 4. CI/CD pipeline

- **Why this exists:** no automated gate currently exists between a commit existing and it being deployed — nothing prevents a broken commit from being manually shipped.
- **Current evidence from repository:** `.github/workflows/` confirmed empty by direct listing.
- **Definition of done:** (1) GitHub Actions workflow runs `python -m pytest tests/` on push/PR to `main`; (2) tested by both a passing and a deliberately-failing commit; (3) verified by the Actions run history showing correct red/green results; (4) documented via a status badge in the root README.
- **How success will be verified:** a linked, real GitHub Actions run URL showing a failed run (from a deliberately broken test) followed by a passing run after the fix.

### 5. Dependency and Docker version pinning

- **Why this exists:** floating tags (`nginx:latest`) and unpinned ranges (frontend `^` deps) mean rebuilds aren't reproducible — undermines CI's long-term value.
- **Current evidence from repository:** confirmed via direct inspection of `docker-compose.yml` (`nginx:latest`, `postgres:15`) and both Dockerfiles (untagged-patch base images); `package.json` confirmed using `^` ranges; `requirements.txt` confirmed already fully pinned.
- **Definition of done:** (1) all image tags pinned to specific versions, frontend Dockerfile uses `npm ci`; (2) tested via a clean `docker compose build`; (3) verified via `docker compose config` showing exact resolved tags; (4) documented as resolved in this tracker and the maturity assessment's risk table.
- **How success will be verified:** `docker compose config` output pasted showing no `latest` or unpinned major-only tags remaining.

---

## Phase 5C — Application Maturity

### 6. JWT refresh token decision and implementation

- **Why this exists:** dead code (`create_refresh_token()`, unused) currently implies a capability that doesn't exist; users are forced to re-authenticate every 15 minutes with no working alternative.
- **Current evidence from repository:** confirmed via repository-wide search — `create_refresh_token` is defined in `auth_utils.py` and never referenced anywhere else in the codebase.
- **Definition of done:** a decision is made (wire up vs. remove) and executed. If wired up: (1) `/auth/refresh` route + token-type enforcement + frontend silent-refresh implemented; (2) tested through a full expire → refresh → continue cycle; (3) verified by confirming token-type rejection works both directions; (4) documented in `PHASE_5_IMPLEMENTATION_PLAN.md`'s outcome and this tracker.
- **How success will be verified:** a real login → wait-for-expiry (or shortened-expiry test) → successful silent refresh → continued authenticated request, all demonstrated with actual request/response evidence, plus confirmation that a refresh token is rejected at a normal protected route and vice versa.

### 7. Expanded automated testing

- **Why this exists:** item 4's CI pipeline currently has almost nothing meaningful to check — only `/chat` has test coverage.
- **Current evidence from repository:** confirmed via direct listing of `tests/routes/` — only `test_chat.py` exists; frontend confirmed to have zero test files.
- **Definition of done:** (1) `test_auth.py` and `test_tasks.py` added, including a cross-user task isolation test; (2) tested locally; (3) verified by intentionally breaking the isolation logic and confirming the new test catches it, then reverting; (4) documented via updated CI status and this tracker.
- **How success will be verified:** `python -m pytest tests/ -v` output showing all tests passing, plus a paired before/after result showing the isolation test failing against a deliberately broken `user_id` filter and passing once reverted.

---

## Phase 5D — AI Engineering Maturity

### 8. Claude usage tracking

- **Why this exists:** token/cost usage is currently invisible — `response.usage` is discarded on every call.
- **Current evidence from repository:** confirmed via direct reading of `claude_client.py` — only `response.content[0].text` is used; `usage` is never accessed.
- **Definition of done:** (1) token counts logged per call; (2) tested via a real `/chat` request; (3) verified by cross-checking logged counts against the Anthropic Console's usage dashboard for the same window; (4) documented in code comments/log format.
- **How success will be verified:** a `docker logs tasklytics_backend` excerpt showing a logged token count, matched against the corresponding entry in the Anthropic Console.

### 9. Prompt versioning

- **Why this exists:** the prompt has no version identifier, making it impossible to know which prompt wording produced any given historical output — a hard blocker for item 10.
- **Current evidence from repository:** confirmed via direct reading of `claude_client.py` — the prompt is an inline f-string with no version marker.
- **Definition of done:** (1) prompt extracted to `app/services/ai/prompts.py` with an explicit version identifier; (2) tested by confirming `/chat` still returns correctly-structured responses post-refactor; (3) verified by confirming the version identifier appears in the item-8 usage log; (4) documented as the new source-of-truth location for the prompt.
- **How success will be verified:** a passing `test_chat.py` run post-refactor, plus a log line showing the version identifier attached to a real request.

### 10. AI evaluation framework

- **Why this exists:** no systematic way exists to detect a quality regression from a prompt or model change — only structural (JSON-shape) breakage is currently detectable at all.
- **Current evidence from repository:** confirmed — no evaluation code/directory exists anywhere in the repository; Phase 4's `/chat` production test is the only prior AI-output check on record, and it validated shape, not content quality.
- **Definition of done:** (1) a versioned assertion-based eval suite (~10-15 scenarios) exists in `tests/ai_eval/`, run against the real Claude API; (2) tested by running it against the current baseline prompt; (3) verified by making a deliberate prompt change and confirming the suite's results actually change for at least one assertion; (4) documented with the baseline results recorded alongside the item-9 prompt version they correspond to.
- **How success will be verified:** two recorded eval runs — one against the baseline prompt, one against a deliberately modified prompt — showing a real, attributable difference in results, proving the suite has actual discriminating power.

---

## Update discipline for this tracker

Each item's row moves from `Not Started` → `In Progress` when work begins, → `Implemented (unverified)` once code/config exists but before verification evidence is captured, → `Complete` only once real Implementation Evidence *and* Verification Evidence are pasted into the summary table (commit hashes, command output, dashboard links — not narrative summaries). This mirrors the exact standard that resolved the Phase 4 backup-status contradiction: a status claim without attached evidence is not a completed item.
