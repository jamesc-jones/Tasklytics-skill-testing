"""Assertion functions for the AI eval suite.

Each function takes (parsed_result, scenario) and returns (passed: bool, message: str).
Kept as plain functions rather than a class hierarchy - a handful of small,
independent checks, not enough structure to justify more machinery.
"""

import re


def non_empty_response(result, scenario):
    ok = bool(result.get("response", "").strip())
    return ok, "ok" if ok else "response field is empty"


def no_parse_error(result, scenario):
    ok = "error" not in result
    return ok, "ok" if ok else f"parse error present: {result.get('error')}"


def priority_tasks_non_empty(result, scenario):
    ok = len(result.get("priority_tasks", [])) > 0
    return ok, "ok" if ok else "priority_tasks is empty"


def mentions_a_real_task(result, scenario):
    """Loose check that the response isn't fully generic - it should reference
    at least one actual task title from the scenario's context, not just
    produce boilerplate unrelated to the real input."""
    tasks_text = scenario["tasks_context"].get("tasks", "")
    titles = re.findall(r"- ([^(]+)\(", tasks_text)

    if not titles:
        return True, "ok (no titles in this scenario to check against)"

    haystack = (
        result.get("response", "") + " " + " ".join(result.get("priority_tasks", []))
    ).lower()

    found = any(title.strip().lower() in haystack for title in titles)
    return found, "ok" if found else "no real task title referenced in response"


ASSERTION_REGISTRY = {
    "non_empty_response": non_empty_response,
    "no_parse_error": no_parse_error,
    "priority_tasks_non_empty": priority_tasks_non_empty,
    "mentions_a_real_task": mentions_a_real_task,
}
