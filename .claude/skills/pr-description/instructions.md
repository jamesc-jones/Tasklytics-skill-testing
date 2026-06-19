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
  - If authentication logic is changed, explicitly flag it as high risk

---

## STEP 3 — Output generation rules

- Be concise
- Prioritize clarity over completeness
- If diff is large:
  - summarize high-level changes first
  - then list key files

---

## STEP 4 — Advanced Handling

### Multiple Commits

If the diff includes multiple commits:

- Identify each commit’s purpose
- Group related changes together
- Summarize at a high level first
- Avoid repeating similar changes across commits
- Focus on overall intent rather than commit-by-commit noise

---

### Large Diffs (Chunking Strategy)

If the diff is very large:

- Do NOT attempt to describe every line change
- Summarize high-level changes first
- Highlight only:
  - critical files
  - major logic changes
  - architectural impact

- Prefer:
  "Refactored task service for performance improvements across multiple modules"
  instead of listing every file

---

### Missing Context Fallback

If the diff or context is incomplete:

- Do NOT guess missing implementation details
- Use neutral phrasing such as:
  - "Updates related to..."
  - "Changes appear to modify..."
  - "Introduces adjustments to..."

- If necessary, clearly state:
  "Some implementation details could not be fully determined from the provided diff."
