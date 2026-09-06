from __future__ import annotations

import json
import unittest
from pathlib import Path

from adaptive_engine import determine_support
from analytics import calculate_metrics
from diagnostic_engine import diagnose_attempt, is_correct_answer
from llm_service import (
    _fallback_support,
    _generated_support,
    _service_error_support,
    assess_generated_support,
    build_prompt,
)
from simulation import SCENARIOS, run_scenario


ROOT = Path(__file__).parents[1]
TASKS = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))


class AdaptivePrototypeTests(unittest.TestCase):
    def test_answer_checking_normalises_expression_formatting(self) -> None:
        self.assertTrue(is_correct_answer("(n%2) == 0", TASKS[0]))
        self.assertTrue(is_correct_answer("n % 2 != 0", TASKS[1]))
        self.assertTrue(is_correct_answer("n%2==1", TASKS[1]))
        self.assertFalse(is_correct_answer("n / 2 == 0", TASKS[0]))

    def test_escalation_and_fading(self) -> None:
        support = 0
        task_events: list[dict] = []
        session_events: list[dict] = []
        for attempt, answer in enumerate(["n / 2 == 0", "n % 2 == 1", "n > 0"], start=1):
            diagnosis = diagnose_attempt(
                answer=answer,
                task=TASKS[0],
                attempt=attempt,
                task_events=task_events,
                session_events=session_events,
            )
            decision = determine_support(
                correct=diagnosis.correct,
                attempt=attempt,
                previous_support=support,
                task_support_cap=4,
            )
            support = decision.support_after
            event = {"correct": diagnosis.correct, "support_level": support, "error_type": diagnosis.error_type}
            task_events.append(event)
            session_events.append(event)
        self.assertEqual(support, 3)

        solved = determine_support(
            correct=True,
            attempt=4,
            previous_support=support,
            task_support_cap=4,
        )
        self.assertEqual(solved.support_after, 2)
        self.assertEqual(solved.direction, "fade")

        task_three_levels = []
        support = 0
        for attempt in range(1, 5):
            decision = determine_support(
                correct=False,
                attempt=attempt,
                previous_support=support,
                task_support_cap=TASKS[2]["support_cap"],
            )
            support = decision.support_after
            task_three_levels.append(support)
        self.assertEqual(task_three_levels, [1, 2, 3, 4])

    def test_prompt_includes_fixed_support_level(self) -> None:
        prompt = build_prompt(
            task=TASKS[0],
            learner_answer="n / 2 == 0",
            attempt=1,
            support_level=1,
            scaffold_type="guiding question",
            previous_errors=0,
        )
        self.assertIn("Pedagogical support level: 1", prompt)
        self.assertIn("do not give the correct answer", prompt.lower())

    def test_compliance_checker_detects_early_solution(self) -> None:
        assessment = assess_generated_support(
            text="Use n % 2 == 0.",
            task=TASKS[0],
            support_level=2,
        )
        self.assertEqual(assessment["no_solution"], 0)

    def test_non_empty_model_response_is_not_replaced_with_task_hint(self) -> None:
        model_text = "Which operator helps you find the remainder after division?"
        generated = _generated_support(model_text, TASKS[0], 1)
        self.assertEqual(generated.status, "generated")
        self.assertEqual(generated.text, model_text)
        fallback = _fallback_support(TASKS[0], 1)
        self.assertEqual(fallback.status, "fallback")
        self.assertIn("remainder", fallback.text)

    def test_quota_error_does_not_show_task_fallback(self) -> None:
        result = _service_error_support(Exception("429 RESOURCE_EXHAUSTED: quota exceeded"))
        self.assertEqual(result.status, "rate_limited")
        self.assertNotIn("remainder", result.text.lower())

    def test_progress_counts_every_displayed_hint(self) -> None:
        records = [
            {
                "task_id": 1,
                "attempt": 1,
                "correct": False,
                "support_level": 1,
                "ai_status": "fallback",
                "ai_compliance_rate": 100,
            },
            {
                "task_id": 1,
                "attempt": 2,
                "correct": False,
                "support_level": 2,
                "ai_status": "generated",
                "ai_compliance_rate": 100,
            },
        ]
        metrics = calculate_metrics(records, current_support=2)
        self.assertEqual(metrics["ai_hints"], 2)

    def test_all_article_scenarios_match_policy(self) -> None:
        for code, scenario in SCENARIOS.items():
            with self.subTest(scenario=code):
                result = run_scenario(TASKS, scenario)
                self.assertTrue(result["matches"])


if __name__ == "__main__":
    unittest.main()
