from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


LOG_COLUMNS = [
    "session_id",
    "task_id",
    "attempt",
    "user_answer",
    "correct",
    "previous_errors",
    "previous_hints",
    "previous_results",
    "support_level",
    "previous_support_level",
    "support_direction",
    "scaffold_type",
    "ai_response",
    "ai_status",
    "ai_type_match",
    "ai_no_solution",
    "ai_relevant",
    "ai_clear",
    "ai_brief",
    "ai_compliance_rate",
    "response_time_sec",
    "timestamp",
]


def append_interaction(record: dict[str, Any], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    row = {column: record.get(column, "") for column in LOG_COLUMNS}
    pd.DataFrame([row]).to_csv(
        destination,
        mode="a",
        header=not destination.exists(),
        index=False,
        encoding="utf-8-sig",
    )
