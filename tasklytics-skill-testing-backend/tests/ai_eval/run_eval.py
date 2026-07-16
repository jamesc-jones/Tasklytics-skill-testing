"""Manual AI evaluation runner for the Claude chat prompt.

Hits the REAL Anthropic API - costs real money, requires a real
ANTHROPIC_API_KEY in the environment. Never run automatically in CI
(this file has no test_ prefix specifically so pytest's default
collection under tests/ never picks it up).

Usage, from tasklytics-skill-testing-backend/:
    python tests/ai_eval/run_eval.py

Run this before and after a deliberate prompt change (app/services/ai/prompts.py)
to check for output-quality regressions structural tests can't catch.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai.claude_client import call_claude
from app.services.ai.response_parser import parse_claude_response
from app.services.ai.prompts import CHAT_PROMPT_VERSION

from scenarios import SCENARIOS
from assertions import ASSERTION_REGISTRY


def run():
    print(f"Running AI eval suite against prompt version: {CHAT_PROMPT_VERSION}\n")
    total = 0
    passed = 0

    for scenario in SCENARIOS:
        raw = call_claude(scenario["tasks_context"], scenario["user_message"])
        parsed = parse_claude_response(raw)

        print(f"[{scenario['name']}]")
        for assertion_name in scenario["assertions"]:
            total += 1
            fn = ASSERTION_REGISTRY[assertion_name]
            ok, message = fn(parsed, scenario)
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            print(f"  {status} - {assertion_name}: {message}")
        print()

    print(f"Result: {passed}/{total} assertions passed")
    return passed == total


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set - this suite calls the real Claude API and needs it.")
        sys.exit(1)

    success = run()
    sys.exit(0 if success else 1)
