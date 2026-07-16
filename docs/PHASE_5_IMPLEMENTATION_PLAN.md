# Tasklytics Phase 5 Implementation Plan

Architect-level roadmap, evidence-based, no code changes made to produce this document. Each item traces to a specific, cited current-state fact (file path, confirmed behavior, or absence thereof) rather than a generic best-practice assumption. Builds on `PHASE_5_MATURITY_ASSESSMENT.md`.

---

## Phase 5A — Reliability Foundation

### 1. Off-server database backups

**Current state:** `pg_dump` runs daily via cron (`0 2 * * *`), retention cleanup at `0 3 * * *` (30-day window), output lands in `/var/backups/tasklytics/` — confirmed via production command output in Phase 4. All backup files live on the same VPS disk as the live database.

**Problem:** a backup's entire purpose is to survive failure of the primary system. A backup stored on the same disk as what it protects doesn't do that — VPS disk failure, accidental deletion, or full VPS loss destroys both simultaneously.

**Proposed solution:** add a sync step, after the nightly dump, pushing `/var/backups/tasklytics/` to off-server object storage — DigitalOcean Spaces (same provider, low account-setup friction, S3-compatible) via `rclone`, a single static binary with no daemon requirement.

**Architectural reasoning:** keep the sync as a separate cron entry/step from the dump itself, not merged into one script — failure isolation, so a sync failure (network blip, credential expiry) doesn't prevent the local dump from succeeding, and a dump failure doesn't attempt to sync a partial/missing file. Use `rclone` specifically because it's provider-agnostic (S3, Spaces, Backblaze, etc. all supported identically) — avoids hard-coupling the backup strategy to one vendor's SDK.

**Tradeoffs:** introduces a new secret (Spaces API key/secret) to manage outside git, consistent with existing `.env` handling; small recurring storage cost (negligible at current data volume); one more host-level tool to keep updated.

**Files affected:** new VPS-only script (e.g. `/usr/local/bin/tasklytics-backup-sync.sh`, not committed to the repo — mirrors how the existing backup cron entries are VPS-local, not repo-tracked); new crontab entry; `rclone` config lives at `~/.config/rclone/rclone.conf` on the VPS, outside git. `docs/PRODUCTION_RUNBOOK.md` and `docs/PRODUCTION_VERIFICATION.md` updated to document the new step once implemented.

**Implementation difficulty:** Low.

**Verification method:** after a sync run, `rclone ls <remote>:<bucket>` should show file count/dates matching `/var/backups/tasklytics/`. Critically, also perform one full restore *from the offsite copy specifically* (download it, restore into a temporary database, verify row counts) — proving the offsite copy is genuinely usable, not merely present.

---

### 2. Uptime monitoring

**Current state:** no automated uptime checking exists. Health verification has only ever happened via manual `curl` commands run during deployment sessions (Phase 4).

**Problem:** an outage is currently discovered only when someone happens to check manually, or a user reports it — there is no proactive detection.

**Proposed solution:** external synthetic monitoring (e.g., UptimeRobot free tier) polling `https://tasklytics2ai.com/api/` on a short interval (e.g., 5 minutes), with email/SMS alerting on failure and recovery.

**Architectural reasoning:** monitoring infrastructure must not share a failure domain with the thing it monitors — a self-hosted monitor running on the same VPS can't report the VPS being down. An external SaaS check is the only architecture that actually satisfies "tell me when this is unreachable."

**Tradeoffs:** third-party dependency (acceptable at free tier, low-stakes for a portfolio-scale app); this checks HTTP-level liveness only — it would not catch "the site returns 200 but the AI endpoint is silently broken." A deeper functional check is possible later but requires handling auth in the monitor, more setup than warranted as a first step.

**Files affected:** none in-repo; document the monitor configuration in `docs/PRODUCTION_RUNBOOK.md` once set up.

**Implementation difficulty:** Low.

**Verification method:** deliberately stop `tasklytics_nginx` and confirm an alert fires within the expected interval; restart and confirm a recovery notification also fires.

---

### 3. Error tracking

**Current state:** no error tracking or APM tool is integrated. Exceptions are visible only via `docker logs tasklytics_backend`, requiring someone to be actively watching or checking after the fact.

**Problem:** a silent failure (an unhandled exception in `response_parser.py`, a Claude API error, a database error) currently goes undetected unless logs are manually inspected at the right time.

**Proposed solution:** integrate Sentry's Python SDK (free tier) into the FastAPI app, initialized in `app/main.py` with a DSN read from a new `SENTRY_DSN` env var — consistent with the existing pattern of secrets living in `.env.docker`, never hardcoded.

**Architectural reasoning:** Sentry captures full stack traces, request context, and automatically groups recurring errors — meaningfully higher signal than grepping raw `docker logs` after the fact, and works passively without anyone needing to be watching.

**Tradeoffs:** sends error context to a third-party service — needs explicit scrubbing configuration to ensure no secrets or user PII leak into captured request context; adds one dependency (`sentry-sdk`) and one required env var.

**Files affected:** `tasklytics-skill-testing-backend/app/main.py` (SDK init), `tasklytics-skill-testing-backend/requirements.txt` (add `sentry-sdk`), `tasklytics-skill-testing-backend/.env.docker.example` (document the new var), VPS `.env.docker` (real DSN, not committed).

**Implementation difficulty:** Low.

**Verification method:** deliberately trigger an unhandled exception (a temporary debug route, or reproducing a known edge case) and confirm it appears in the Sentry dashboard with a complete, real stack trace.

---

## Phase 5B — Deployment Engineering

### 4. CI/CD pipeline

**Current state:** `.github/workflows/` is empty — confirmed by direct listing. Every deploy to date has been a manual `git pull` + `docker compose up -d --build` run on the VPS by hand.

**Problem:** no automated gate exists between "a commit exists" and "a commit is deployed" — nothing currently prevents a broken commit from being manually deployed, and there's no independent record of "this commit's tests passed" separate from a person's say-so.

**Proposed solution:** a GitHub Actions workflow running `python -m pytest tests/` on every push/PR to `main`, reusing the existing in-memory SQLite test setup already defined in `tests/conftest.py`. Scoped deliberately to **test-on-push only, not auto-deploy** — actually deploying from CI to the live VPS would require SSH secrets stored in GitHub and a real rollback story, both disproportionate risk additions for a single-VPS app with no rollback tooling yet (see item 5's pinning work as a prerequisite for that being safe later).

**Architectural reasoning:** separates "is this code known-good" (CI — low risk, no production access) from "is this code live" (manual deploy — a deliberate, reviewable action). This captures most of CI/CD's safety value without taking on automated-production-deploy risk before the foundations (version pinning, broader test coverage) are in place.

**Tradeoffs:** CI is only as valuable as what it tests — with current coverage (one file, `test_chat.py`), initial value is limited until item 7 lands; sequencing item 4 first is still correct, since a thin-but-real pipeline is easy to grow, whereas broad tests with no pipeline running them provide false confidence.

**Files affected:** new `.github/workflows/backend-tests.yml`.

**Implementation difficulty:** Medium — the main risk is correctly replicating the local test environment (working directory, the `python -m pytest` vs. bare `pytest` distinction already documented in `CLAUDE.md` regarding `sys.path` resolution).

**Verification method:** push a commit with a deliberately failing test, confirm the Actions run reports red; push a fix, confirm it goes green. A passing-build badge in the root README also serves as portfolio evidence.

---

### 5. Dependency and Docker version pinning

**Current state:** `docker-compose.yml` uses `nginx:latest` (floating) and `postgres:15` (major-version only); both Dockerfiles use untagged-patch base images (`python:3.11-slim`, `node:20`). Backend `requirements.txt` is fully pinned (`==` throughout, confirmed). Frontend `package.json` uses `^` ranges (unpinned minor/patch), though `package-lock.json` exists.

**Problem:** floating or loose version references mean a rebuild at a different point in time can silently pull a different image or dependency version than what was last tested — reproducibility isn't guaranteed, which undermines the value of CI (item 4): a green build today doesn't necessarily mean the same thing next month if the underlying images have drifted.

**Proposed solution:** pin `nginx` to a specific tag (e.g., `nginx:1.27-alpine`, incidentally also shrinking image size), pin `postgres` to a specific minor (e.g., `postgres:15.8`), pin both Dockerfiles' base images to specific patch tags. For the frontend, switch the Dockerfile from `npm install` to `npm ci` — installs exactly what's locked in `package-lock.json`, sidestepping the practical risk of `^` ranges in `package.json` without needing to change that file.

**Architectural reasoning:** reproducibility is a prerequisite for CI (item 4) to mean anything durable — pairing this with the already-recommended Dependabot means version bumps become deliberate, reviewed pull requests instead of silent, automatic changes on next rebuild.

**Tradeoffs:** pinned images require manual, deliberate version bumps rather than automatically receiving patches — an ongoing (small) maintenance task, mitigated by Dependabot surfacing when a bump is available rather than relying on floating tags to silently apply it.

**Files affected:** `docker-compose.yml` (image tags), `tasklytics-skill-testing-backend/Dockerfile`, `tasklytics-skill-testing-frontend/Dockerfile` (base image tags, `npm install` → `npm ci`).

**Implementation difficulty:** Low.

**Verification method:** `docker compose build` succeeds cleanly with the pinned tags; `docker compose config` shows the exact resolved versions (no `latest`); confirm the `npm ci`-built `dist/` output is functionally equivalent to the current `npm install`-built output (frontend loads and behaves identically).

---

## Phase 5C — Application Maturity

### 6. JWT refresh token decision and implementation

**Current state:** `app/auth/auth_utils.py` defines `create_refresh_token()` (7-day expiry, `"type": "refresh"` claim) but it is **never called anywhere in the codebase** — confirmed via repository-wide search. `/auth/login` (`app/routes/auth.py`) issues only a 15-minute access token via `create_access_token()`.

**Problem:** this is currently neither a decision nor a working feature — it's half-built, unused code implying a capability (silent session refresh) that does not exist. Users are forced to re-authenticate every 15 minutes.

**Proposed solution — a decision point, not a foregone conclusion:**
- **Option A (wire it up):** add `POST /auth/refresh`, accepting a refresh token, validating via `decode_token()` and checking `type == "refresh"`, issuing a new access token. Frontend (`src/context/AuthContext.jsx`, `src/api/api.js`) needs a silent-refresh path — on a `401`, attempt `/auth/refresh` before forcing logout.
- **Option B (remove it):** delete `create_refresh_token` and `REFRESH_TOKEN_EXPIRE_DAYS`, keep the 15-minute-only model as the deliberate, documented UX.
- **Recommendation:** Option A — forced re-login every 15 minutes is a materially worse UX than the added complexity of a refresh flow, and the token-creation groundwork already exists.

**Architectural reasoning:** the existing `"type"` claim already distinguishes access from refresh tokens at the payload level — implementation mainly requires `get_current_user` (`app/auth/auth_dependencies.py`) to reject any token where `type != "access"`, and the new `/refresh` route to reject any token where `type != "refresh"`. This keeps the two token types from being interchangeable, which matters given their very different risk profiles (see Tradeoffs).

**Tradeoffs:** refresh tokens meaningfully widen the theft blast-radius window — 7 days vs. 15 minutes — and no revocation mechanism exists for either token type today (already a documented risk in Phase 4's carry-forward list). Implementing refresh tokens without at least a "revoke on password change" mechanism makes an existing gap more consequential, not less; worth scoping that in alongside this item rather than after.

**Files affected:** `app/auth/auth_utils.py`, `app/routes/auth.py` (new route), `app/auth/auth_dependencies.py` (token-type enforcement), `src/context/AuthContext.jsx`, `src/api/api.js`.

**Implementation difficulty:** Medium.

**Verification method:** full manual cycle test — login, let the access token expire (or temporarily shorten expiry for testing), confirm a normal request returns `401`, confirm `/auth/refresh` issues a working new access token without forcing re-login, and confirm an access token is rejected at `/auth/refresh` while a refresh token is rejected at ordinary protected routes (proving the type check actually discriminates, not just accepts anything valid-signed).

---

### 7. Expanded automated testing

**Current state:** `tasklytics-skill-testing-backend/tests/routes/test_chat.py` is the only test file — confirmed by direct listing. No tests exist for registration, login, task CRUD, admin routes, or the legacy `/ai/task-insights` endpoint. Frontend has zero test files and no test runner configured.

**Problem:** item 4's CI pipeline is only as valuable as what it checks — today, a green CI run says almost nothing about whether auth or task management actually still work.

**Proposed solution:** extend backend coverage first, prioritizing auth (register/login, and the refresh flow from item 6 if implemented) and task CRUD — specifically including a cross-user isolation test (user A cannot read/modify user B's tasks), since that's the concrete security property `CLAUDE.md` documents as enforced by `user_id` filtering throughout `app/routes/tasks.py`. Reuse the existing `conftest.py` fixtures (`db_session`, `client`, `test_user`, `auth_headers`) rather than introducing a new test pattern.

**Architectural reasoning:** prioritize tests by "would this have caught a real, previously-identified risk" rather than by raw coverage percentage — a cross-user isolation test directly validates a security property this project has already documented as load-bearing, making it higher-value than, say, testing a getter method with no branching logic.

**Tradeoffs:** real time investment; frontend testing specifically requires standing up test infrastructure from zero (no runner configured today) — meaningfully higher effort than extending the existing backend suite, so it's deliberately deferred (consistent with the maturity assessment's Tier 3 ranking) rather than bundled into this item.

**Files affected:** new `tests/routes/test_auth.py`, `tests/routes/test_tasks.py`; possible extension of `tests/conftest.py` (e.g., a second seeded user, needed for the cross-user isolation test).

**Implementation difficulty:** Medium.

**Verification method:** `python -m pytest tests/ -v` passing locally and in CI (item 4). To prove the new tests have real discriminating power (not just trivially passing), deliberately introduce a bug locally — e.g., remove a `user_id` filter from a task query — and confirm the new isolation test actually fails; then revert and confirm it passes again.

---

## Phase 5D — AI Engineering Maturity

### 8. Claude usage tracking

**Current state:** `app/services/ai/claude_client.py`'s `call_claude()` calls `client.messages.create(...)` and returns only `response.content[0].text`. The Anthropic SDK response includes a `usage` field (input/output token counts) that is currently discarded.

**Problem:** no visibility into per-request token consumption or approximate cost — a prompt change that significantly increases token usage would currently go unnoticed except by manually checking the Anthropic Console after the fact.

**Proposed solution:** log `response.usage.input_tokens` / `response.usage.output_tokens` (plus a computed approximate cost, using Claude's public per-model pricing) alongside each call, to the existing log stream — no new infrastructure. Persisting to a database table is explicitly *not* proposed yet; revisit only if usage volume grows enough to justify historical trend analysis.

**Architectural reasoning:** start with the cheapest possible observability (a structured log line) rather than building a database table or dashboard ahead of evidence that volume justifies it — directly consistent with the "avoid unnecessary complexity" constraint given this project's current traffic scale.

**Tradeoffs:** log-based tracking supports spot-checking, not trend analysis or automated cost-spike alerting — an accepted limitation for now, revisit once Sentry (item 3) is in place and structured-log correlation becomes easier.

**Files affected:** `app/services/ai/claude_client.py`.

**Implementation difficulty:** Low.

**Verification method:** trigger a `/chat` request, confirm `docker logs tasklytics_backend` shows a log line with real token counts, and cross-check those counts against the Anthropic Console's usage dashboard for the same request window.

---

### 9. Prompt versioning

**Current state:** the Claude prompt is an inline f-string literal inside `call_claude()` in `claude_client.py`. No version identifier exists; the only history is git's line-level diff for that file.

**Problem:** if a prompt edit causes a regression (output quality, or a `response_parser.py` parsing failure), there's currently no fast way to determine which prompt version produced a given historical output, and no structured way to compare prompt variants.

**Proposed solution:** extract the prompt to its own module (`app/services/ai/prompts.py`, mirroring the existing `app/ai/prompts.py` pattern already used by the legacy system) with an explicit version identifier (string or date), and include that identifier in the item-8 usage log line — so any logged request traces back to the exact prompt wording that produced it.

**Architectural reasoning:** a low-cost structural change (moving a string into a named, versioned constant) that is a direct prerequisite for item 10 — you cannot meaningfully compare "did this prompt change help or hurt" without knowing which version produced which past result.

**Tradeoffs:** minimal — primarily code organization. The only ongoing cost is the discipline of bumping the version identifier on future edits, a process habit rather than a technical burden.

**Files affected:** new `app/services/ai/prompts.py`; `app/services/ai/claude_client.py` (import prompt from new location, log version alongside usage).

**Implementation difficulty:** Low.

**Verification method:** confirm `/chat` still returns correctly-structured responses post-refactor (regression-checked via `test_chat.py`), and confirm the version identifier appears correctly in the item-8 log line.

---

### 10. AI evaluation framework

**Current state:** no systematic evaluation exists. Prompt/output quality has only ever been assessed via manual, ad hoc testing during deployment sessions — the Phase 4 `/chat` production test confirmed the response was *correctly shaped* JSON, not that its *content* was good.

**Problem:** without a repeatable evaluation set, there is no way to detect a quality regression caused by a prompt change, a model version change, or a `response_parser.py` change — only structural (JSON-shape) breakage is currently detectable at all.

**Proposed solution:** a small, versioned set of representative test scenarios (roughly 10-15 realistic task-list situations) evaluated via *assertions* about expected output properties, rather than exact-match golden outputs (more practical given inherent LLM output variability) — e.g., "`priority_tasks` should be non-empty when the input contains overdue tasks," "the response should reference task titles actually present in the provided context." Run against the real Claude API (not mocked — the goal is evaluating actual model behavior), manually or on a deliberately infrequent schedule, before a prompt or model change is considered complete.

**Architectural reasoning:** this is the most novel item on the roadmap and the one most directly relevant to demonstrating applied "Claude Architect"-level judgment specifically — deliberately scoped as a lightweight assertion suite rather than adopting a full eval platform (e.g., promptfoo or a custom scored-rubric system), which would be disproportionate to this application's actual current needs. A small, real suite demonstrates the same underlying skill without the operational overhead of a platform this app doesn't yet need.

**Tradeoffs:** real API calls cost real money and take real time — not suitable for running on every CI push. Recommend running manually or on a separate, infrequent trigger (only before a deliberate prompt/model change), explicitly not part of the item-4 CI pipeline. Assertion-based checks are inherently less precise than exact-match comparison, an accepted tradeoff given non-determinism, not an oversight.

**Files affected:** new `tasklytics-skill-testing-backend/tests/ai_eval/` directory, kept structurally separate from the regular `pytest` suite specifically because it hits the live Anthropic API and must never run automatically on every commit.

**Implementation difficulty:** Medium-High — the highest-difficulty item in this plan; a genuinely new pattern for this codebase, not an extension of existing infrastructure.

**Verification method:** run the suite against the current (item 9-versioned) prompt baseline, record pass/fail per assertion. Then make a deliberate prompt change and re-run — confirming the suite's result actually changes for at least one assertion. This proves the suite has real discriminating power rather than being a set of checks that always pass regardless of input.

---

## Sequencing note

This plan intentionally follows the 5A → 5B → 5C → 5D order given, which also happens to be a sound dependency chain: reliability foundations (5A) require no other Phase 5 work first; CI (5B, item 4) is more valuable once pinning (5B, item 5) makes it reproducible, and both are prerequisites for expanded testing (5C, item 7) being trustworthy; the AI maturity items (5D) are sequenced internally as usage tracking → prompt versioning → evaluation, since evaluation (item 10) explicitly depends on prompt versioning (item 9) to be meaningful.

No implementation has begun. This document is planning only, per instruction.
