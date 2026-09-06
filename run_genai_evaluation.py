from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from adaptive_engine import SCAFFOLD_TYPES
from llm_service import generate_support


ROOT = Path(__file__).parent
WRONG_ANSWERS = {
    1: "n / 2 == 0",
    2: "n % 2 == 1",
    3: "n > 0",
    4: "True",
}


def main() -> None:
    tasks = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))
    task = tasks[0]
    rows = []
    for support_level in range(1, 5):
        for repetition in range(1, 6):
            response = generate_support(
                task=task,
                learner_answer=WRONG_ANSWERS[support_level],
                attempt=support_level,
                support_level=support_level,
                scaffold_type=SCAFFOLD_TYPES[support_level],
                previous_errors=support_level - 1,
            )
            rows.append(
                {
                    "generation_id": f"L{support_level}-{repetition}",
                    "support_level": support_level,
                    "response_status": response.status,
                    "response_text": response.text,
                    "type_match": response.type_match,
                    "no_solution_before_level_4": response.no_solution,
                    "relevant_to_task": response.relevant,
                    "clear": response.clear,
                    "brief": response.brief,
                    "compliance_rate": response.compliance_rate,
                }
            )

    results = pd.DataFrame(rows)
    destination = ROOT / "results"
    destination.mkdir(exist_ok=True)
    results.to_csv(destination / "genai_evaluation_20.csv", index=False, encoding="utf-8-sig")

    generated = results[results["response_status"] == "generated"]
    criteria = ["type_match", "no_solution_before_level_4", "relevant_to_task", "clear", "brief"]
    passed = int(generated[criteria].sum().sum()) if not generated.empty else 0
    total = int(len(generated) * len(criteria))
    summary = pd.DataFrame(
        [
            {
                "planned_requests": len(results),
                "model_responses": len(generated),
                "fallback_or_unavailable": len(results) - len(generated),
                "criteria_passed": passed,
                "criteria_total": total,
                "compliance_rate_percent": round((passed / total) * 100, 1) if total else 0.0,
            }
        ]
    )
    summary.to_csv(destination / "genai_evaluation_summary.csv", index=False, encoding="utf-8-sig")
    print("Created the 20-response evaluation and compliance summary in results.")


if __name__ == "__main__":
    main()
