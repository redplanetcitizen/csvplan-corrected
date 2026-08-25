"""Read-only smoke test for an extracted csvplan_corrected package."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from csvplan_corrected import SolverConfig, default_data_paths, run_default


def main() -> None:
    root = Path(__file__).resolve().parent
    required = [
        root / "pyproject.toml",
        root / "README.md",
        root / "MODEL_NOTES.md",
        *default_data_paths(),
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("File mancanti: " + ", ".join(missing))

    result = run_default(
        config=SolverConfig(strict=False, verbose=False, max_iterations=3000)
    )
    scenario = result["scenario"]
    reports = scenario.constraint_report
    if not reports or not all(report.compliant for report in reports):
        raise SystemExit("Verifica dei vincoli fallita")
    if np.min(scenario.net_output) < -1e-8:
        raise SystemExit("Output netto negativo")
    history = np.asarray(result["objective_history"], dtype=float)
    if history.size > 1 and np.any(np.diff(history) <= 0.0):
        raise SystemExit("L'obiettivo non cresce monotonicamente")

    summary = {
        "status": "OK",
        "years": scenario.prob.horizon,
        "products": scenario.prob.products,
        "iterations": result["iterations"],
        "stop_reason": result["stop_reason"],
        "mean_harmony": scenario.meanh,
        "minimum_net_output": float(np.min(scenario.net_output)),
        "all_constraints_compliant": True,
        "terminal_capital_limited": bool(scenario.terminal_capital_limited),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
