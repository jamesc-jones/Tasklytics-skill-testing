# PR Description Instructions

## STEP 1 — Get diff (in order):

1. Use pasted diff if available

2. Otherwise run:
- git diff main...HEAD
- git diff master...HEAD
- git diff origin/main...HEAD

3. If needed:
- git show HEAD
- git show <sha>

4. If all fail:
Ask the user for git diff output

If no diff is available:
Write a draft only if necessary:
"DRAFT — written from description only"

---

## STEP 2 — Understand changes

- Identify files changed
- Determine intent:
  - feature
  - fix
  - refactor
  - chore

- Flag risky changes:
  - database changes
  - auth logic
  - breaking changes

---

## STEP 3 — Output generation rules

- Be concise
- Prioritize clarity over completeness
- If diff is large:
  - summarize high-level changes first
  - then list key files