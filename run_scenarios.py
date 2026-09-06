from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from simulation import run_all_scenarios


ROOT = Path(__file__).parent


def main() -> None:
    tasks = json.loads((ROOT / "data" / "tasks.json").read_text(encoding="utf-8"))
    results = pd.DataFrame(run_all_scenarios(tasks))
    destination = ROOT / "results" / "scenario_results.csv"
    destination.parent.mkdir(exist_ok=True)
    results.to_csv(destination, index=False, encoding="utf-8-sig")
    print(f"Created file: {destination}")


if __name__ == "__main__":
    main()
