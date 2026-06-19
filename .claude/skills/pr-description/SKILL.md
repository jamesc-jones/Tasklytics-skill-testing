---
name: pr-description
description: >
  Generates structured pull request descriptions.

  Trigger this skill whenever the user:
  - asks for a PR description, PR desc, or PR writeup
  - asks to summarize code changes
  - pastes a git diff or git show
  - asks to describe changes or a commit

  Always use this skill for PR-related documentation tasks.
---

You are writing a pull request description.

You MUST always use exactly these four sections in this order:

## What
## Why
## Changes
## Risks / Notes

Do not rename, reorder, or add sections.

---

STEP 1 — Get diff (in order):
1. Use pasted diff if available
2. Run:
   - git diff main...HEAD
   - git diff master...HEAD
   - git diff origin/main...HEAD
3. If needed:
   - git show HEAD
   - git show <sha>
4. If all fail, ask user for git diff output

If no diff is available, write a draft only if necessary:
"DRAFT — written from description only"

---

STEP 2 — Understand changes:
- Identify files changed
- Determine intent (feature, fix, refactor, chore)
- Flag risky changes

---

STEP 3 — Output format (STRICT):

## What
One sentence describing the change.

## Why
1–3 sentences explaining motivation.

## Changes
- Bullet list of key changes (files, functions, behavior)

## Risks / Notes
- Bullet list of risks or "None identified."
