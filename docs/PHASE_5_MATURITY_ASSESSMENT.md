# Tasklytics Phase 5 Production Maturity Assessment

Evidence-based, consistent with the Phase 4 documentation standard. No code has been modified to produce this assessment — it is inspection and analysis only, per instruction.

## 1. Current maturity level

**Tier: Stable single-host production — verified functional, weak on operational feedback loops.**

Tasklytics has cleared the bar most side projects never reach: real HTTPS with automated renewal, a hardened host (firewall, SSH, Fail2Ban), non-root containers, automated backups, and — critically — actual production-verified functionality (not just "deployed," but proven working end-to-end, including both AI subsystems, with real command output as evidence). That's a genuinely defensible "this works and I can prove it" position.

What keeps it from the next tier up is not security or correctness — it's **feedback and repeatability**: no CI/CD (every deploy is a manual, unverified action), no error tracking (a production exception is invisible unless someone happens to `docker logs` at the right moment), no uptime alerting (an outage is discovered by a user, not by the system), and thin test coverage (one backend test file, zero frontend tests). These are the gaps that separate "I hardened and verified this by hand, carefully, once" from "this system tells me when something's wrong and stops me from breaking it again."

## 2. Strengths

- **HTTPS with automated, verified renewal** (webroot-authenticated, chosen deliberately to avoid the port-80 conflict with containerized nginx)
- **Host hardening**: UFW default-deny with only 22/80/443 open, SSH key-only with root login disabled, Fail2Ban actively banning real scan traffic
- **Non-root container execution**, confirmed by direct test (not just Dockerfile inspection) during Phase 2
- **Fail-fast configuration checks**: both `SECRET_KEY` and `ANTHROPIC_API_KEY` raise at module import if unset — the app refuses to start in a half-configured state rather than failing unpredictably later
- **Argon2 password hashing** (via `passlib`) — a modern, deliberately-chosen algorithm, not a default left unexamined
- **Automated backups, verified actually running** (not just configured) — cron entries, real dated files, active service, confirmed via production command output
- **Docker healthchecks and log rotation**, confirmed applied on live containers, not just present in source
- **An unusually rigorous documentation and verification culture** for a project this size — the Phase 4 docs distinguish "verified from production output" vs. "reported" vs. "not verified" and that discipline caught a real contradiction (backup status) that could otherwise have shipped undetected. This is itself a portfolio asset — it demonstrates engineering judgment, not just implementation.
- **Secrets hygiene going forward**: `.env` files gitignored, `docker-compose.yml` parameterized rather than hardcoded, with the one known historical exposure explicitly documented rather than hidden

## 3. Remaining risks

Consolidated from Phase 4's carry-forward list plus new findings from this inspection:

| Risk | Severity | Notes |
|---|---|---|
| No CI/CD — every deploy is manual, untested by automation | High | Confirmed: `.github/workflows/` is empty |
| JWT refresh token infrastructure exists but is unused — users hard-logged-out every 15 minutes | Medium | Confirmed via source: `create_refresh_token()` defined, never called |
| No error tracking — a production exception is only visible via manual log inspection | Medium-High | No Sentry/equivalent in `requirements.txt` |
| No uptime/alerting — outages are discovered reactively | Medium-High | No monitoring service configured |
| Backups exist only on the same VPS disk as the data they protect | Medium | Already documented in Phase 4; unresolved |
| Restore procedure not re-tested since the Postgres credential rotation | Medium | Already documented in Phase 4; unresolved |
| Thin test coverage (one backend test file, zero frontend tests) | Medium | Confirmed by direct inspection |
| `nginx:latest` floating tag; frontend deps use `^` ranges | Low-Medium | Unpredictable version drift on rebuild |
| No dependency vulnerability scanning | Low-Medium | No Dependabot config or equivalent found |
| Original leaked Postgres password remains in git history | Low | Rotated live; documented, accepted tradeoff |
| No AI cost/token usage tracking | Low | Not urgent at current traffic scale |
| Legacy AI system has no documented deprecation plan | Low | Both systems verified functional; coexistence is a choice, not yet a decision |

## 4. Recommended Phase 5 priorities, ranked by impact

Ranked by (impact on real risk reduction) ÷ (implementation complexity), staying within the single-VPS constraint — nothing below recommends infrastructure beyond what one host can reasonably run.

**Tier 1 — high impact, low complexity (do first):**
1. **Off-server backup copy** — a scheduled `rclone`/`rsync` job pushing `/var/backups/tasklytics/` to an object storage bucket (e.g., DigitalOcean Spaces, since you're already on DO). Directly closes the single-point-of-failure gap explicitly flagged in every Phase 4 doc.
2. **Uptime monitoring + alerting** — an external service (e.g., UptimeRobot's free tier) pinging `https://tasklytics2ai.com/api/` and alerting on failure. Zero infrastructure to run yourself; closes the "outage discovered by a user" gap entirely.
3. **Error tracking (Sentry)** — a few lines of SDK initialization in `app/main.py`. Immediately surfaces production exceptions (including any AI/parsing failures) without needing to be watching logs live.
4. **Resolve the dead refresh-token code** — either wire up a real `/auth/refresh` endpoint + frontend silent-refresh (better UX, moderate effort) or remove the unused functions (low effort, at minimum stops the code from implying a capability that doesn't exist). Either answer is fine; leaving it as-is is the only wrong answer, since it's currently misleading.
5. **Pin `nginx:latest` to a specific version** — a one-line change, removes an unpredictable-upgrade risk on next rebuild.
6. **Enable Dependabot** (or equivalent) — a single config file, flags known-vulnerable dependencies automatically going forward.

**Tier 2 — high impact, moderate complexity:**
7. **CI pipeline (GitHub Actions)** running the existing backend test suite on every push, blocking merge/deploy on failure. Directly addresses the "no automated gate" risk and is a strong, visible portfolio signal (a green checkmark badge on the repo).
8. **Expand backend test coverage** — auth flow and task CRUD are the highest-value gaps (currently only `/chat` has tests). Do this alongside CI, not before it — a CI pipeline with thin coverage is still more valuable than thick coverage nobody runs automatically.
9. **Re-run the restore drill** against current configuration (post credential-rotation) — cheap, closes a specifically-flagged Phase 4 carry-forward item.

**Tier 3 — real value, but lower urgency at current scale:**
10. **Per-endpoint rate limiting** — differentiate the AI endpoints (`/chat`, `/ai/task-insights`) from cheap CRUD endpoints, since AI calls carry real per-request cost. Current nginx rate limiting is a single global zone.
11. **AI token/cost logging** — log token usage per Claude call. Low urgency at current traffic, but cheap to add now before it's needed for real cost investigation later.
12. **Frontend test coverage** — currently zero; lower priority than backend given the app's complexity is concentrated server-side (auth, AI orchestration, data integrity).

**Tier 4 — worth naming, not recommending yet:**
13. **Centralized log aggregation (Loki) / metrics stack (Prometheus+Grafana)** — genuine operational value, but a meaningful new maintenance surface (more containers, more things that can themselves fail) for a single-VPS app whose current debugging needs are already served by `docker logs` + the existing runbook. **Worth naming a real exception here**: if the goal includes demonstrating observability-stack experience specifically for portfolio/certification purposes, that's a legitimate reason to build this anyway, distinct from operational necessity — that's a call only you can make, since it trades "proportionate to actual need" for "proportionate to what you want to demonstrate." Flagging the tension rather than deciding it for you.
14. **Zero-downtime deployment (blue-green on a single VPS)** — real engineering technique, but meaningful added complexity for a personal-scale app where a few seconds of deploy-time downtime is an acceptable tradeoff today.

**Portfolio/interview track (parallel, not sequential to the above):**
15. **README and repository presentation overhaul** — architecture diagram (already exists in `docs/DEPLOYMENT_ARCHITECTURE.md`, needs to be surfaced in the root README where a reviewer actually looks first), a clear "what this demonstrates" framing, and links to the Phase 4/5 evidence docs as proof of engineering process. Given the stated goal explicitly includes hiring-manager/interview evaluation, this is disproportionately high-value for its effort relative to most Tier 3 items — a reviewer will read the README before they read any code.

## 5. Suggested implementation roadmap

Not a rigid schedule — a sequencing logic, since several items are prerequisites for others (CI before expanded tests are worth much; error tracking before you'd notice whether the AI parser's one-known-fragility-case ever actually triggers in the wild).

1. **Week 1 — cheap risk reduction:** off-server backups, uptime monitoring, Sentry, nginx version pin, Dependabot, decide-and-resolve the refresh token question, re-run the restore drill.
2. **Week 2 — repeatability:** CI pipeline against current tests, then expand backend test coverage (auth + tasks), running against the new pipeline as it grows.
3. **Week 3 — refinement:** per-endpoint rate limiting, AI token/cost logging.
4. **Ongoing / parallel:** README and portfolio presentation — this doesn't block or depend on the technical work above and can happen alongside it.
5. **Deferred, revisit only if scale or portfolio goals specifically call for it:** metrics/log-aggregation stack, zero-downtime deploys, frontend test suite.

## 6. Estimated difficulty per item

| Item | Difficulty | Why |
|---|---|---|
| Off-server backup copy | Low | One `rclone`/`rsync` cron job |
| Uptime monitoring | Low | External service, no infrastructure |
| Sentry error tracking | Low | SDK init, a few lines |
| Resolve refresh-token dead code | Low–Medium | Low if removing; Medium if wiring up a real refresh flow + frontend silent-refresh |
| Pin `nginx:latest` | Low | One-line change |
| Dependabot | Low | One config file |
| CI pipeline | Medium | GitHub Actions workflow, needs care around the test DB/env setup already documented in `CLAUDE.md`/`conftest.py` |
| Expand backend test coverage | Medium | Auth + tasks CRUD, moderate volume of new test code |
| Restore drill re-test | Low | Re-run an already-documented procedure |
| Per-endpoint rate limiting | Low–Medium | nginx config change, needs careful testing to avoid breaking legitimate traffic |
| AI token/cost logging | Low–Medium | Anthropic SDK responses include usage data; needs a place to persist/log it |
| Frontend tests | Medium–High | No existing test infrastructure to build on (confirmed: zero test files, no test runner configured) |
| Metrics/log-aggregation stack | High | New containers, new maintenance surface, genuinely more complex |
| Zero-downtime deploys | High | Requires either a load balancer in front of two app instances or a more involved single-host blue-green setup |
| README/portfolio overhaul | Low–Medium | Writing effort, not technical complexity |
