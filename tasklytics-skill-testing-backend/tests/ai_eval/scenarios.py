"""Representative scenarios for the /chat -> ChatAgent -> Claude pipeline.

Kept small and hand-curated (not generated) - the point is a handful of
realistic situations with clear expected properties, not exhaustive coverage.
Add a scenario here when a real prompt regression is found, so the suite
grows from actual failure modes rather than speculation.
"""

SCENARIOS = [
    {
        "name": "overdue_high_priority_task_should_be_flagged",
        "tasks_context": {
            "tasks": (
                "- Finish quarterly report (Priority: high, Due: 2026-07-01)\n"
                "- Read a book (Priority: low, Due: No due date)"
            ),
            "stats": {"total": 2, "completed": 0, "completion_rate": 0},
        },
        "user_message": "What should I focus on today?",
        "assertions": [
            "non_empty_response",
            "no_parse_error",
            "priority_tasks_non_empty",
            "mentions_a_real_task",
        ],
    },
    {
        "name": "no_tasks_should_not_crash_or_fabricate",
        "tasks_context": {
            "tasks": "No tasks available.",
            "stats": {"total": 0, "completed": 0, "completion_rate": 0},
        },
        "user_message": "What should I focus on today?",
        "assertions": [
            "non_empty_response",
            "no_parse_error",
        ],
    },
    {
        "name": "all_tasks_completed_should_acknowledge_progress",
        "tasks_context": {
            "tasks": "- Ship the report (Priority: high, Due: No due date)",
            "stats": {"total": 1, "completed": 1, "completion_rate": 1.0},
        },
        "user_message": "How am I doing?",
        "assertions": [
            "non_empty_response",
            "no_parse_error",
        ],
    },
]
