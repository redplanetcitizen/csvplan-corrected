from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np


OUT = Path("comparison")
SF = Path("sourceforge")


def _floats_semicolon(text: str) -> np.ndarray:
    return np.asarray([float(x) for x in text.strip().split(";") if x != ""], dtype=float)


def parse_julia_output(path: Path):
    initial = None
    choices = []
    final = None
    final_investments = None
    final_goal_ratios = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("TRACE_INITIAL,"):
            parts = line.split(",", 3)
            initial = {
                "mean": float(parts[1]),
                "std": float(parts[2]),
                "h": _floats_semicolon(parts[3]),
            }
        elif line.startswith("TRACE_CHOICE,"):
            parts = line.split(",", 5)
            choices.append(
                {
                    "destination_year": int(parts[1]) - 1,
                    "source_year": int(parts[2]) - 1,
                    "gain": float(parts[3]),
                    "mean_after": float(parts[4]),
                    "h_after": _floats_semicolon(parts[5]),
                }
            )
        elif line.startswith("TRACE_FINAL,"):
            parts = line.split(",", 5)
            final = {
                "iterations_counter": int(parts[1]),
                "mean": float(parts[2]),
                "std": float(parts[3]),
                "cv": float(parts[4]),
                "h": _floats_semicolon(parts[5]),
            }
        elif line.startswith("TRACE_FINAL_INVESTMENTS,"):
            final_investments = _floats_semicolon(line.split(",", 1)[1])
        elif line.startswith("TRACE_FINAL_GOALRATIOS,"):
            final_goal_ratios = _floats_semicolon(line.split(",", 1)[1])
    if initial is None or final is None:
        raise RuntimeError("instrumented Julia trace markers not found")
    return initial, choices, final, final_investments, final_goal_ratios


def read_year_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def numeric_csv(path: Path):
    return np.loadtxt(path, delimiter=",", skiprows=1)


def main():
    initial, choices, final, julia_inv, julia_ratios = parse_julia_output(SF / "julia_output.txt")
    legacy_trace = json.loads((OUT / "legacy_trace.json").read_text(encoding="utf-8"))
    accepted_legacy = [row for row in legacy_trace if row["accepted"]]
    year_rows = read_year_csv(OUT / "year_comparison.csv")

    n = min(len(choices), len(accepted_legacy))
    trace_rows = []
    max_source_dest_mismatch = 0
    max_gain_diff = 0.0
    max_mean_diff = 0.0
    max_h_diff = 0.0
    first_mismatch = None
    for k in range(n):
        j = choices[k]
        p = accepted_legacy[k]
        source_match = j["source_year"] == p["source_year"]
        dest_match = j["destination_year"] == p["destination_year"]
        mismatch = int(not (source_match and dest_match))
        max_source_dest_mismatch = max(max_source_dest_mismatch, mismatch)
        gain_diff = abs(j["gain"] - p["best_gain"])
        mean_diff = abs(j["mean_after"] - p["mean_after"])
        h_diff = float(np.max(np.abs(j["h_after"] - np.asarray(p["h_after"], dtype=float))))
        max_gain_diff = max(max_gain_diff, gain_diff)
        max_mean_diff = max(max_mean_diff, mean_diff)
        max_h_diff = max(max_h_diff, h_diff)
        if first_mismatch is None and (mismatch or gain_diff > 1e-10 or mean_diff > 1e-10 or h_diff > 1e-10):
            first_mismatch = k + 1
        trace_rows.append(
            [
                k + 1,
                j["source_year"] + 1,
                p["source_year"] + 1,
                j["destination_year"] + 1,
                p["destination_year"] + 1,
                j["gain"],
                p["best_gain"],
                gain_diff,
                j["mean_after"],
                p["mean_after"],
                mean_diff,
                h_diff,
            ]
        )

    legacy_h_final = np.asarray(accepted_legacy[-1]["h_after"] if accepted_legacy else [], dtype=float)
    final_h_diff = float(np.max(np.abs(final["h"] - legacy_h_final))) if legacy_h_final.size else float("nan")

    legacy_inv = np.asarray([float(row["legacy_investment_total"]) for row in year_rows], dtype=float)
    legacy_ratios = np.asarray([float(row["legacy_goal_scale"]) for row in year_rows], dtype=float)

    input_checks = {}
    for name in ("jeuflows.csv", "jeucap.csv", "jeudep.csv", "jeulabtargs.csv"):
        sf = numeric_csv(SF / name)
        repo = numeric_csv(Path("csvplan_corrected/data") / name)
        input_checks[name] = {
            "shape_sourceforge": list(sf.shape),
            "shape_repo": list(repo.shape),
            "max_abs_numeric_difference": float(np.max(np.abs(sf - repo))) if sf.shape == repo.shape else None,
        }

    summary = {
        "sourceforge_input_checks": input_checks,
        "julia": {
            "accepted_choices": len(choices),
            "iterations_counter": final["iterations_counter"],
            "initial_mean_harmony": initial["mean"],
            "initial_std_harmony": initial["std"],
            "final_mean_harmony": final["mean"],
            "final_std_harmony": final["std"],
            "final_cv": final["cv"],
        },
        "legacy_vs_julia": {
            "legacy_accepted_choices": len(accepted_legacy),
            "choice_count_difference": len(choices) - len(accepted_legacy),
            "all_source_destination_choices_match": max_source_dest_mismatch == 0 and len(choices) == len(accepted_legacy),
            "max_abs_gain_difference": max_gain_diff,
            "max_abs_mean_after_difference": max_mean_diff,
            "max_abs_harmony_vector_difference_over_trace": max_h_diff,
            "first_trace_mismatch_at_move": first_mismatch,
            "final_harmony_vector_max_abs_difference": final_h_diff,
            "final_investment_total_max_abs_difference": (
                float(np.max(np.abs(julia_inv - legacy_inv))) if julia_inv is not None and julia_inv.shape == legacy_inv.shape else None
            ),
            "final_goal_ratio_max_abs_difference": (
                float(np.max(np.abs(julia_ratios - legacy_ratios))) if julia_ratios is not None and julia_ratios.shape == legacy_ratios.shape else None
            ),
        },
    }

    with (OUT / "julia_vs_legacy_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    with (OUT / "julia_vs_legacy_trace.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "move",
                "julia_source",
                "legacy_source",
                "julia_destination",
                "legacy_destination",
                "julia_gain",
                "legacy_gain",
                "gain_abs_diff",
                "julia_mean_after",
                "legacy_mean_after",
                "mean_abs_diff",
                "h_vector_max_abs_diff",
            ]
        )
        writer.writerows(trace_rows)

    print("JULIA_VS_LEGACY_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
