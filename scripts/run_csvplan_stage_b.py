from __future__ import annotations

"""One-factor Stage B audit for csvplan controller/code-only ambiguities.

Baseline is the verified historical matrix prototype.  No Stage A correction is
combined into these runs: each B variant changes exactly one controller or
initialisation choice relative to ``csvplan.jl``.
"""

from dataclasses import dataclass, asdict
import copy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


BASEFILE = Path(__file__).with_name("run_csvplan_stage_a.py")
spec = importlib.util.spec_from_file_location("csvplan_stage_a_base_for_b", BASEFILE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Stage A switch module")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

OUT = Path("comparison/stage_b")
OUT.mkdir(parents=True, exist_ok=True)
HISTORICAL_VARIANT = m.Variant("historical_local_rules")


@dataclass(frozen=True)
class BVariant:
    name: str
    preliminary_level: float = legacy.INITIAL_INVESTMENT_LEVEL
    destination_mode: str = "sequential_below_mean"  # or global_lowest
    epsilon: float = legacy.EPSILON
    no_transfer_mode: str = "stop_immediately"  # or continue_scan


TEXT_FIRST_SUGGESTION_EPSILON = 1.0 / (1.0 + legacy.DEPRECIATION_HORIZON)

VARIANTS = [
    BVariant("baseline_csvplan_jl"),
    BVariant("B1_C14_preliminary_70pct_off", preliminary_level=0.0),
    BVariant("B2_C05_global_lowest_destination", destination_mode="global_lowest"),
    BVariant("B3_C07_text_first_suggestion_epsilon", epsilon=TEXT_FIRST_SUGGESTION_EPSILON),
    BVariant("B4_C24_continue_after_failed_destination", no_transfer_mode="continue_scan"),
]


def build_initial(preliminary_level: float) -> legacy.Scenario:
    problem = legacy.readInProblem(*legacy.default_data_paths())
    _, lastgoal = legacy.For_the_last_year_of_the_plan_return_a_net_output_target(
        problem.TheLastYear - 1,
        problem.A,
        problem.D,
        problem.g,
        problem.labouravailable,
    )
    problem.g[problem.TheLastYear - 1, :] = lastgoal

    output = np.vstack(
        [legacy.grossOutputForDemandf(problem.g[i, :], problem.A) for i in range(problem.TheLastYear)]
    )
    stock = legacy.Assign_to_each_year_capital_stock(problem.caps, problem.dep, problem.TheLastYear)
    investments = np.zeros(
        (problem.TheLastYear, problem.caprows, problem.capcols), dtype=np.float64
    )

    if preliminary_level != 0.0:
        preliminary = preliminary_level * (problem.caps * problem.dep)
        for year in range(problem.TheLastYear - 1):
            investments[year] = preliminary
            # Historical matrix-prototype propagation, including its timing semantics.
            legacy.update_subsequent_years_capital(year + 1, preliminary, problem.dep, stock)

    s = legacy.Scenario(
        problem,
        output,
        stock,
        investments,
        np.zeros(problem.TheLastYear),
        np.zeros(problem.TheLastYear),
        0.0,
        0.0,
        np.zeros((problem.TheLastYear, problem.capcols)),
        [np.zeros(problem.capcols) for _ in range(problem.TheLastYear)],
        problem.g.copy(),
    )
    legacy.update_outputs(s)
    legacy.computeHarmonies(s)
    return s


def attempt(s: legacy.Scenario, dest: int, epsilon: float):
    target = legacy.harmonyInverse(s.meanh)
    current = legacy.harmonyInverse(s.h[dest])
    scale_increment = float((target - current) * epsilon)

    current_stock = s.si[dest]
    n, _ = current_stock.shape
    additional_capital = np.maximum(current_stock * scale_increment, 0.0)
    best_year = None
    best_gain = 0.0
    best_scenario = s
    candidate_rows = []

    for source in range(dest):
        source_capital = additional_capital
        # Historical default: inverse depreciation is disabled.
        newscenario = copy.deepcopy(s)
        legacy.updateScenario(newscenario, source, source_capital)
        gain = float(newscenario.meanh - s.meanh)
        posflags = s.netoutputs[source][:n] > np.zeros(n)
        feasible = bool(np.prod(posflags))
        candidate_rows.append(
            {
                "source_year": source,
                "gain": gain,
                "historical_precheck": feasible,
            }
        )
        if gain > best_gain and feasible:
            best_year = source
            best_gain = gain
            best_scenario = newscenario

    return best_scenario, best_year, best_gain, scale_increment, candidate_rows


def run_sequential(v: BVariant, s: legacy.Scenario):
    trace = []
    iter_count = 1
    accepted = 0
    attempts = 0
    doagain = True
    stop_reason = None

    while doagain:
        accepted_this_pass = 0
        failed_this_pass = 0
        for dest in range(1, s.prob.TheLastYear):
            cv = float(s.stdh / abs(s.meanh))
            if cv < legacy.MINCOEFF or iter_count > legacy.MAXITER:
                stop_reason = "cv" if cv < legacy.MINCOEFF else "maxiter"
                doagain = False
                break
            iter_count += 1

            if doagain and s.h[dest] < s.meanh:
                attempts += 1
                before = float(s.meanh)
                cand, source, gain, scale, candidates = attempt(s, dest, v.epsilon)
                if source is None:
                    failed_this_pass += 1
                    trace.append(
                        {
                            "counter": iter_count,
                            "destination_year": dest,
                            "source_year": None,
                            "accepted": False,
                            "mean_before": before,
                            "mean_after": before,
                            "best_gain": 0.0,
                            "scale_increment": scale,
                            "candidates": candidates,
                        }
                    )
                    if v.no_transfer_mode == "stop_immediately":
                        # Historical behaviour: set flag false but finish the scan,
                        # incrementing the displayed counter without further moves.
                        doagain = False
                else:
                    s = cand
                    accepted += 1
                    accepted_this_pass += 1
                    trace.append(
                        {
                            "counter": iter_count,
                            "destination_year": dest,
                            "source_year": int(source),
                            "accepted": True,
                            "mean_before": before,
                            "mean_after": float(s.meanh),
                            "best_gain": float(gain),
                            "scale_increment": scale,
                        }
                    )

        if not doagain:
            break
        if v.no_transfer_mode == "continue_scan" and accepted_this_pass == 0 and failed_this_pass > 0:
            stop_reason = "no_transfer_full_pass"
            doagain = False
        elif v.no_transfer_mode == "continue_scan" and accepted_this_pass == 0:
            stop_reason = "no_below_mean_correction"
            doagain = False

    return s, trace, iter_count, accepted, attempts, stop_reason


def run_global_lowest(v: BVariant, s: legacy.Scenario):
    trace = []
    iter_count = 1
    accepted = 0
    attempts = 0
    stop_reason = None

    while True:
        cv = float(s.stdh / abs(s.meanh))
        if cv < legacy.MINCOEFF:
            stop_reason = "cv"
            break
        if iter_count > legacy.MAXITER:
            stop_reason = "maxiter"
            break

        dest = int(np.argmin(s.h))  # exact conceptual global minimum, including year 1
        attempts += 1
        iter_count += 1
        before = float(s.meanh)
        cand, source, gain, scale, candidates = attempt(s, dest, v.epsilon)
        if source is None:
            stop_reason = "no_transfer"
            trace.append(
                {
                    "counter": iter_count,
                    "destination_year": dest,
                    "source_year": None,
                    "accepted": False,
                    "mean_before": before,
                    "mean_after": before,
                    "best_gain": 0.0,
                    "scale_increment": scale,
                    "candidates": candidates,
                }
            )
            break
        s = cand
        accepted += 1
        trace.append(
            {
                "counter": iter_count,
                "destination_year": dest,
                "source_year": int(source),
                "accepted": True,
                "mean_before": before,
                "mean_after": float(s.meanh),
                "best_gain": float(gain),
                "scale_increment": scale,
            }
        )

    return s, trace, iter_count, accepted, attempts, stop_reason


def run(v: BVariant):
    s = build_initial(v.preliminary_level)
    initial = {
        "mean_harmony": float(s.meanh),
        "std_harmony": float(s.stdh),
        "cv": float(s.stdh / abs(s.meanh)),
        "min_harmony": float(np.min(s.h)),
        "harmony": s.h.tolist(),
        "investment_total": float(np.sum(s.investments)),
    }

    if v.destination_mode == "global_lowest":
        s, trace, counter, accepted, attempts, stop = run_global_lowest(v, s)
    else:
        s, trace, counter, accepted, attempts, stop = run_sequential(v, s)

    net = np.vstack(s.netoutputs)
    return {
        "variant": asdict(v),
        "initial": initial,
        "final": {
            "iterations_counter": int(counter),
            "accepted_moves": int(accepted),
            "attempted_corrections": int(attempts),
            "stop_reason": stop,
            "mean_harmony": float(s.meanh),
            "sum_harmony": float(np.sum(s.h)),
            "std_harmony": float(s.stdh),
            "cv": float(s.stdh / abs(s.meanh)),
            "min_harmony": float(np.min(s.h)),
            "harmony": s.h.tolist(),
            "goal_fulfilment": s.goal_fullfilment_ratio_vector.tolist(),
            "investment_totals": legacy.investmentsByTypeandYear(s.investments).sum(axis=1).tolist(),
            "min_net_output": float(np.min(net)),
            "negative_net_output_cells": int(np.sum(net < 0.0)),
        },
        "trace": trace,
    }


def first_divergence(base: dict, other: dict, tol: float = 1e-12):
    b0 = np.asarray(base["initial"]["harmony"])
    o0 = np.asarray(other["initial"]["harmony"])
    if np.max(np.abs(b0 - o0)) > tol:
        return {"stage": "initial_harmony"}
    bt = base["trace"]
    ot = other["trace"]
    for i in range(min(len(bt), len(ot))):
        b, o = bt[i], ot[i]
        if (
            b["destination_year"] != o["destination_year"]
            or b["source_year"] != o["source_year"]
            or b["accepted"] != o["accepted"]
            or abs(b["mean_after"] - o["mean_after"]) > tol
        ):
            return {
                "stage": "trace",
                "attempt_index": i + 1,
                "baseline": {k: b.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
                "variant": {k: o.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
            }
    if len(bt) != len(ot):
        return {"stage": "trace_length", "baseline": len(bt), "variant": len(ot)}
    return None


def main():
    results = {v.name: run(v) for v in VARIANTS}
    base = results["baseline_csvplan_jl"]

    oracle = legacy.run_default(False)
    os = oracle["scenario"]
    assert oracle["iterations"] == base["final"]["iterations_counter"]
    assert oracle["stop_reason"] == base["final"]["stop_reason"]
    np.testing.assert_allclose(os.h, base["final"]["harmony"], rtol=0.0, atol=3e-15)

    summary = {
        "baseline_oracle_check": "PASS",
        "historical_epsilon": legacy.EPSILON,
        "text_first_suggestion_epsilon_for_14_year_horizon": TEXT_FIRST_SUGGESTION_EPSILON,
        "baseline": base["final"],
        "variants": {},
    }
    for name, result in results.items():
        if name == "baseline_csvplan_jl":
            continue
        f = result["final"]
        bf = base["final"]
        summary["variants"][name] = {
            "first_divergence": first_divergence(base, result),
            "initial_mean_harmony": result["initial"]["mean_harmony"],
            "initial_investment_total": result["initial"]["investment_total"],
            "final_mean_harmony": f["mean_harmony"],
            "delta_mean_harmony_vs_baseline": f["mean_harmony"] - bf["mean_harmony"],
            "final_sum_harmony": f["sum_harmony"],
            "final_cv": f["cv"],
            "delta_cv_vs_baseline": f["cv"] - bf["cv"],
            "final_min_harmony": f["min_harmony"],
            "delta_min_harmony_vs_baseline": f["min_harmony"] - bf["min_harmony"],
            "accepted_moves": f["accepted_moves"],
            "attempted_corrections": f["attempted_corrections"],
            "iterations_counter": f["iterations_counter"],
            "stop_reason": f["stop_reason"],
            "negative_net_output_cells": f["negative_net_output_cells"],
        }

    (OUT / "stage_b_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "stage_b_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_STAGE_B_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
