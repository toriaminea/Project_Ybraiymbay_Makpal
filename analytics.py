from __future__ import annotations

from typing import Any

import pandas as pd

from logger import LOG_COLUMNS


def session_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=LOG_COLUMNS)
    return pd.DataFrame(records).reindex(columns=LOG_COLUMNS)


def calculate_metrics(records: list[dict[str, Any]], current_support: int) -> dict[str, int | float]:
    frame = session_dataframe(records)
    if frame.empty:
        return {
            "completed_tasks": 0,
            "attempts": 0,
            "errors": 0,
            "correct_rate": 0.0,
            "first_try_correct": 0,
            "ai_hints": 0,
            "max_support": 0,
            "current_support": current_support,
            "ai_compliance_rate": 0.0,
        }

    attempts = len(frame)
    correct_count = int(frame["correct"].astype(bool).sum())
    completed_tasks = int(frame.loc[frame["correct"].astype(bool), "task_id"].nunique())
    first_rows = frame.sort_values(["task_id", "attempt"]).groupby("task_id", as_index=False).first()
    generated = frame[frame["ai_status"] == "generated"]
    provided_hints = frame[frame["ai_status"].isin(["generated", "fallback"])]
    compliance = float(generated["ai_compliance_rate"].astype(float).mean()) if not generated.empty else 0.0
    return {
        "completed_tasks": completed_tasks,
        "attempts": attempts,
        "errors": attempts - correct_count,
        "correct_rate": round((correct_count / attempts) * 100, 1),
        "first_try_correct": int(first_rows["correct"].astype(bool).sum()),
        "ai_hints": int(len(provided_hints)),
        "max_support": int(frame["support_level"].astype(int).max()),
        "current_support": current_support,
        "ai_compliance_rate": round(compliance, 1),
    }
