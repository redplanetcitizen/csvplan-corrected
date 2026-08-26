from __future__ import annotations

"""Stage A runner with exact historical outer-loop/counter semantics.

The switch implementations live in ``run_csvplan_stage_a.py``.  This wrapper
corrects only the audit harness loop: Cockshott's matrix prototype sets its
``doagain`` flag false after a failed transfer but finishes the current scan,
so the displayed iteration counter continues to advance even though no further
moves are attempted.
"""

import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


BASE = Path(__file__).with_name("run_csvplan_stage_a.py")
spec = importlib.util.spec_from_file_location("csvplan_stage_a_base", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Stage A base module")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

OUT = Path("comparison/stage_a")
OUT.mkdir(parents=True, exist_ok=True)


def run_exact(variant):
    s = m._build_initial(variant)
    initial = {
        "mean_harmony": float(s.meanh),
        "std_harmony": float(s.stdh),
        "cv": float(s.stdh / abs(s.meanh)),
        "min_harmony": float(np.min(s.h)),
        "harmony": s.h.tolist(),
        "min_net_output": float(np.min(np.vstack(s.netoutputs))),
    }

    trace = []
    iter_count = 1
    doagain = True
    stop_reason = None
    accepted_moves = 0
    attempted_corrections = 0

    while doagain:
        for destination_year in range(1, s.prob.TheLastYear):
            cv_abs = float(s.stdh / abs(s.meanh))
            if cv_abs < legacy.MINCOEFF or iter_count > legacy.MAXITER:
                stop_reason = "cv" if cv_abs < legacy.MINCOEFF else "maxiter"
                doagain = False
                break
            iter_count += 1

            # Exact matrix-prototype control structure: after a failed transfer
            # doagain is false, but the rest of the current for-loop still runs
            # and increments the counter while suppressing further corrections.
            if doagain and s.h[destination_year] < s.meanh:
                attempted_corrections += 1
                target = legacy.harmonyInverse(s.meanh)
                current = legacy.harmonyInverse(s.h[destination_year])
                scale_increment = float((target - current) * legacy.EPSILON)
                before = s
                candidate, source_year, best_gain, candidates = m._attempt_scale_up(
                    s, destination_year, scale_increment, variant
                )
                if source_year is None:
                    stop_reason = "no_transfer"
                    doagain = False
                    trace.append(
                        {
                            "counter": iter_count,
                            "destination_year": destination_year,
                            "source_year": None,
                            "accepted": False,
                            "mean_before": float(before.meanh),
                            "mean_after": float(before.meanh),
                            "best_gain": 0.0,
                            "candidates": candidates,
                        }
                    )
                else:
                    s = candidate
                    accepted_moves += 1
                    trace.append(
                        {
                            "counter": iter_count,
                            "destination_year": destination_year,
                            "source_year": int(source_year),
                            "accepted": True,
                            "mean_before": float(before.meanh),
                            "mean_after": float(s.meanh),
                            "best_gain": float(best_gain),
                        }
                    )
        if not doagain:
            break

    net = np.vstack(s.netoutputs)
    investment_totals = legacy.investmentsByTypeandYear(s.investments).sum(axis=1)
    return {
        "variant": m.asdict(variant),
        "initial": initial,
        "final": {
            "iterations_counter": int(iter_count),
            "accepted_moves": int(accepted_moves),
            "attempted_corrections": int(attempted_corrections),
            "stop_reason": stop_reason,
            "mean_harmony": float(s.meanh),
            "sum_harmony": float(np.sum(s.h)),
            "std_harmony": float(s.stdh),
            "cv": float(s.stdh / abs(s.meanh)),
            "min_harmony": float(np.min(s.h)),
            "harmony": s.h.tolist(),
            "goal_fulfilment": s.goal_fullfilment_ratio_vector.tolist(),
            "investment_totals": investment_totals.tolist(),
            "min_net_output": float(np.min(net)),
            "negative_net_output_cells": int(np.sum(net < 0.0)),
            "min_capital_stock": float(np.min(s.si)),
        },
        "trace": trace,
    }


def main():
    results = {variant.name: run_exact(variant) for variant in m.VARIANTS}
    baseline = results["baseline_csvplan_jl"]

    packaged = legacy.run_default(False)
    ps = packaged["scenario"]
    bf = baseline["final"]
    assert packaged["iterations"] == bf["iterations_counter"]
    assert packaged["stop_reason"] == bf["stop_reason"]
    np.testing.assert_allclose(ps.h, bf["harmony"], rtol=0.0, atol=3e-15)
    np.testing.assert_allclose(
        legacy.investmentsByTypeandYear(ps.investments).sum(axis=1),
        bf["investment_totals"],
        rtol=0.0,
        atol=1e-8,
    )

    summary = {
        "baseline_oracle_check": "PASS",
        "baseline": baseline["final"],
        "variants": {},
    }
    for name, result in results.items():
        if name == "baseline_csvplan_jl":
            continue
        f = result["final"]
        summary["variants"][name] = {
            "first_divergence": m._first_divergence(baseline, result),
            "initial_mean_harmony": result["initial"]["mean_harmony"],
            "final_mean_harmony": f["mean_harmony"],
            "delta_mean_harmony_vs_baseline": f["mean_harmony"] - baseline["final"]["mean_harmony"],
            "final_sum_harmony": f["sum_harmony"],
            "final_cv": f["cv"],
            "delta_cv_vs_baseline": f["cv"] - baseline["final"]["cv"],
            "final_min_harmony": f["min_harmony"],
            "delta_min_harmony_vs_baseline": f["min_harmony"] - baseline["final"]["min_harmony"],
            "accepted_moves": f["accepted_moves"],
            "attempted_corrections": f["attempted_corrections"],
            "iterations_counter": f["iterations_counter"],
            "stop_reason": f["stop_reason"],
            "min_net_output": f["min_net_output"],
            "negative_net_output_cells": f["negative_net_output_cells"],
        }

    (OUT / "stage_a_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "stage_a_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_STAGE_A_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
