from __future__ import annotations

from dataclasses import dataclass


SCAFFOLD_TYPES = {
    0: "independent work",
    1: "guiding question",
    2: "conceptual hint",
    3: "expanded support",
    4: "corrective explanation",
}


@dataclass(frozen=True)
class SupportDecision:
    support_before: int
    support_after: int
    scaffold_type: str
    direction: str


def determine_support(
    *,
    correct: bool,
    attempt: int,
    previous_support: int,
    task_support_cap: int = 4,
) -> SupportDecision:
    if correct:
        support_after = max(0, previous_support - 1)
    else:
        support_after = min(4, task_support_cap, max(1, attempt, previous_support))

    if correct and support_after < previous_support:
        direction = "fade"
    elif not correct and support_after > previous_support:
        direction = "increase"
    elif support_after == 0:
        direction = "none"
    else:
        direction = "stable"

    return SupportDecision(
        support_before=previous_support,
        support_after=support_after,
        scaffold_type=SCAFFOLD_TYPES[support_after],
        direction=direction,
    )
