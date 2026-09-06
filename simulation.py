from __future__ import annotations

from typing import Any

from adaptive_engine import SCAFFOLD_TYPES, determine_support
from diagnostic_engine import diagnose_attempt


SCENARIOS = {
    "S1": {
        "description": "All tasks are solved on the first attempt.",
        "answers": [["n % 2 == 0"], ["n % 2 != 0"], ["3"]],
        "expected_max_support": 0,
        "expected_final_support": 0,
        "expected_scaffold": "independent work",
    },
    "S2": {
        "description": "One incorrect answer followed by a correct answer.",
        "answers": [["n / 2 == 0", "n % 2 == 0"], ["n % 2 != 0"], ["3"]],
        "expected_max_support": 1,
        "expected_final_support": 0,
        "expected_scaffold": "guiding question",
    },
    "S3": {
        "description": "Two incorrect answers followed by a correct answer.",
        "answers": [["n / 2 == 0", "n % 2 == 1", "n % 2 == 0"], ["n % 2 != 0"], ["3"]],
        "expected_max_support": 2,
        "expected_final_support": 0,
        "expected_scaffold": "conceptual hint",
    },
    "S4": {
        "description": "Persistent difficulty: four consecutive incorrect answers.",
        "answers": [["n / 2 == 0", "n % 2 == 1", "n > 0", "True"]],
        "expected_max_support": 4,
        "expected_final_support": 4,
        "expected_scaffold": "corrective explanation",
    },
    "S5": {
        "description": "Errors in Task 1 followed by independent success and fading support.",
        "answers": [["n / 2 == 0", "n % 2 == 1", "n > 0", "n % 2 == 0"], ["n % 2 != 0"], ["3"]],
        "expected_max_support": 3,
        "expected_final_support": 0,
        "expected_scaffold": "scaffold fading",
    },
    "S6": {
        "description": "Independent completion without errors.",
        "answers": [["n % 2 == 0"], ["n % 2 == 1"], ["3"]],
        "expected_max_support": 0,
        "expected_final_support": 0,
        "expected_scaffold": "independent work",
    },
}


def run_scenario(tasks: list[dict[str, Any]], scenario: dict[str, Any]) -> dict[str, Any]:
    support = 0
    session_events: list[dict[str, Any]] = []
    for task, scripted_answers in zip(tasks, scenario["answers"]):
        task_events: list[dict[str, Any]] = []
        solved = False
        for attempt, answer in enumerate(scripted_answers, start=1):
            diagnosis = diagnose_attempt(
                answer=answer,
                task=task,
                attempt=attempt,
                task_events=task_events,
                session_events=session_events,
            )
            decision = determine_support(
                correct=diagnosis.correct,
                attempt=attempt,
                previous_support=support,
                task_support_cap=task.get("support_cap", 4),
            )
            support = decision.support_after
            event = {
                "task_id": task["id"],
                "attempt": attempt,
                "correct": diagnosis.correct,
                "support_level": support,
                "scaffold_type": decision.scaffold_type,
                "support_direction": decision.direction,
                "error_type": diagnosis.error_type,
            }
            task_events.append(event)
            session_events.append(event)
            if diagnosis.correct:
                solved = True
                break
        if not solved:
            break

    max_event = max(session_events, key=lambda event: event["support_level"], default=None)
    max_support = max_event["support_level"] if max_event else 0
    expected_scaffold = scenario["expected_scaffold"]
    if expected_scaffold == "scaffold fading":
        scaffold_matches = any(event["support_direction"] == "fade" for event in session_events)
        actual_scaffold = "scaffold fading" if scaffold_matches else "not achieved"
    else:
        actual_scaffold = max_event["scaffold_type"] if max_event else SCAFFOLD_TYPES[0]
        scaffold_matches = actual_scaffold == expected_scaffold

    return {
        "max_support": max_support,
        "final_support": support,
        "actual_scaffold": actual_scaffold,
        "trace": " → ".join(str(event["support_level"]) for event in session_events),
        "matches": (
            max_support == scenario["expected_max_support"]
            and support == scenario["expected_final_support"]
            and scaffold_matches
        ),
    }


def run_all_scenarios(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for code, scenario in SCENARIOS.items():
        result = run_scenario(tasks, scenario)
        rows.append(
            {
                "scenario": code,
                "expected_support": scenario["expected_max_support"],
                "actual_support": result["max_support"],
                "expected_scaffold": scenario["expected_scaffold"],
                "actual_scaffold": result["actual_scaffold"],
                "support_trace": result["trace"],
                "compliance": "matches" if result["matches"] else "does not match",
            }
        )
    return rows
