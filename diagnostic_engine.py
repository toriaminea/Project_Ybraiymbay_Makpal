from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosticResult:
    correct: bool
    attempt: int
    error_type: str | None
    repeated_error: bool
    previous_errors: int
    previous_hints: int
    previous_results: tuple[bool, ...]


def _expression_fingerprint(source: str) -> str | None:
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except (SyntaxError, ValueError):
        return None
    return ast.dump(tree.body, annotate_fields=True, include_attributes=False)


def is_correct_answer(answer: str, task: dict[str, Any]) -> bool:
    cleaned = answer.strip()
    if not cleaned:
        return False
    if task["answer_kind"] == "integer":
        return cleaned in {str(value).strip() for value in task["accepted_answers"]}

    answer_fingerprint = _expression_fingerprint(cleaned)
    accepted = {_expression_fingerprint(value) for value in task["accepted_answers"]}
    return answer_fingerprint is not None and answer_fingerprint in accepted


def classify_error(answer: str, task: dict[str, Any]) -> str:
    cleaned = answer.strip()
    if not cleaned:
        return "empty_answer"
    if task["answer_kind"] == "integer":
        return "wrong_output"
    if _expression_fingerprint(cleaned) is None:
        return "syntax_error"

    compact = "".join(cleaned.split())
    if "/" in compact and "%" not in compact:
        return "division_instead_of_remainder"
    if "%2" in compact:
        return "incorrect_remainder_condition"
    return "other_expression"


def diagnose_attempt(
    *,
    answer: str,
    task: dict[str, Any],
    attempt: int,
    task_events: list[dict[str, Any]],
    session_events: list[dict[str, Any]],
) -> DiagnosticResult:
    correct = is_correct_answer(answer, task)
    error_type = None if correct else classify_error(answer, task)
    previous_error_types = [event.get("error_type") for event in task_events if event.get("error_type")]
    previous_results = tuple(bool(event.get("correct")) for event in session_events)
    return DiagnosticResult(
        correct=correct,
        attempt=attempt,
        error_type=error_type,
        repeated_error=bool(error_type and error_type in previous_error_types),
        previous_errors=sum(not bool(event.get("correct")) for event in task_events),
        previous_hints=sum(int(event.get("support_level", 0)) > 0 for event in session_events),
        previous_results=previous_results,
    )
