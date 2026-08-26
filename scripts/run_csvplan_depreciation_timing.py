from __future__ import annotations

"""Isolate source-to-destination depreciation timing in Cockshott's matrix prototype.

All variants keep the historical 70% preliminary schedule and its historical stock
path.  Only *endogenous correction transfers* are changed.  This avoids the Stage
A5 confound where changing forward depreciation also changed the preliminary
initial state.
"""

from dataclasses import dataclass, asdict
import copy
import json
from pathlib import Path

import numpy as np

from csvplan_corrected import legacy


OUT = Path("comparison/depreciation_timing")
OUT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Variant:
    name: str
    inverse_mode: str = "off"  # off, historical_latent, exact
    forward_mode: str = "historical"  # historical, exact_endogenous


VARIANTS = [
    Variant("baseline_csvplan_jl"),
    Variant("D1_C11a_inverse_on_historical_latent_timing", inverse_mode="historical_latent"),
    Variant("D2_C11b_inverse_on_exact_timing", inverse_mode="exact"),
    Variant("D3_C16_exact_forward_timing_endogenous_only", forward_mode="exact_endogenous"),
    Variant("D4_C11_C16_exact_inverse_and_forward", inverse_mode="exact", forward_mode="exact_endogenous"),
]


def build_initial() -> legacy.Scenario:
    """Exact historical initial state, including the 70% preliminary schedule."""
    p = legacy.readInProblem(*legacy.default_data_paths())
    _, lastgoal = legacy.For_the_last_year_of_the_plan_return_a_net_output_target(
        p.TheLastYear - 1, p.A, p.D, p.g, p.labouravailable
    )
    p.g[p.TheLastYear - 1, :] = lastgoal
    O = np.vstack([legacy.grossOutputForDemandf(p.g[i, :], p.A) for i in range(p.TheLastYear)])
    stock = legacy.Assign_to_each_year_capital_stock(p.caps, p.dep, p.TheLastYear)
    investments = np.zeros((p.TheLastYear, p.caprows, p.capcols), dtype=np.float64)
    prelim = legacy.INITIAL_INVESTMENT_LEVEL * (p.caps * p.dep)
    for y in range(p.TheLastYear - 1):
        legacy.setup_preliminary_investment_schedule(y, investments, prelim, p.dep, stock)
    s = legacy.Scenario(
        p, O, stock, investments,
        np.zeros(p.TheLastYear), np.zeros(p.TheLastYear), 0.0, 0.0,
        np.zeros((p.TheLastYear, p.capcols)),
        [np.zeros(p.capcols) for _ in range(p.TheLastYear)],
        p.g.copy(),
    )
    legacy.update_outputs(s)
    legacy.computeHarmonies(s)
    return s


def exact_inverse(arrival: np.ndarray, source: int, dest: int, dep: np.ndarray) -> np.ndarray:
    periods = dest - source - 1
    if periods < 0:
        raise ValueError("source must precede destination")
    survival = np.power(1.0 - dep, periods)
    if np.any(survival <= 0.0):
        raise ValueError("non-positive survival in exact inverse depreciation")
    return arrival / survival


def update_candidate(s: legacy.Scenario, source: int, capital: np.ndarray, forward_mode: str) -> legacy.Scenario:
    s2 = copy.deepcopy(s)
    s2.investments[source] += capital
    if forward_mode == "historical":
        legacy.update_subsequent_years_capital(source + 1, capital, s2.prob.dep, s2.si)
    elif forward_mode == "exact_endogenous":
        first_available = source + 1
        for y in range(first_available, s2.prob.TheLastYear):
            periods = y - first_available
            s2.si[y] += capital * np.power(1.0 - s2.prob.dep, periods)
    else:
        raise ValueError(forward_mode)
    legacy.update_outputs(s2)
    legacy.computeHarmonies(s2)
    return s2


def attempt(s: legacy.Scenario, dest: int, v: Variant):
    target = legacy.harmonyInverse(s.meanh)
    current = legacy.harmonyInverse(s.h[dest])
    scale = float((target - current) * legacy.EPSILON)
    additional_at_dest = np.maximum(s.si[dest] * scale, 0.0)
    n, _ = additional_at_dest.shape
    best_source = None
    best_gain = 0.0
    best_scenario = s
    candidates = []
    for source in range(dest):
        if v.inverse_mode == "off":
            source_capital = additional_at_dest
        elif v.inverse_mode == "historical_latent":
            source_capital = legacy.inversedepreciate(
                additional_at_dest, dest - 1 - source, s.prob.dep
            )
        elif v.inverse_mode == "exact":
            source_capital = exact_inverse(additional_at_dest, source, dest, s.prob.dep)
        else:
            raise ValueError(v.inverse_mode)
        candidate = update_candidate(s, source, source_capital, v.forward_mode)
        gain = float(candidate.meanh - s.meanh)
        feasible = bool(np.prod(s.netoutputs[source][:n] > np.zeros(n)))
        candidates.append({
            "source_year": source,
            "gain": gain,
            "historical_precheck": feasible,
            "source_capital_total": float(np.sum(source_capital)),
        })
        if gain > best_gain and feasible:
            best_source = source
            best_gain = gain
            best_scenario = candidate
    return best_scenario, best_source, best_gain, scale, candidates


def run(v: Variant):
    s = build_initial()
    initial_h = s.h.copy()
    trace = []
    counter = 1
    accepted = 0
    attempts = 0
    doagain = True
    stop = None
    while doagain:
        for dest in range(1, s.prob.TheLastYear):
            cv = float(s.stdh / abs(s.meanh))
            if cv < legacy.MINCOEFF or counter > legacy.MAXITER:
                stop = "cv" if cv < legacy.MINCOEFF else "maxiter"
                doagain = False
                break
            counter += 1
            if doagain and s.h[dest] < s.meanh:
                attempts += 1
                before = float(s.meanh)
                cand, source, gain, scale, candidates = attempt(s, dest, v)
                if source is None:
                    stop = "no_transfer"
                    doagain = False
                    trace.append({
                        "counter": counter, "destination_year": dest, "source_year": None,
                        "accepted": False, "mean_before": before, "mean_after": before,
                        "best_gain": 0.0, "scale": scale, "candidates": candidates,
                    })
                else:
                    s = cand
                    accepted += 1
                    trace.append({
                        "counter": counter, "destination_year": dest, "source_year": int(source),
                        "accepted": True, "mean_before": before, "mean_after": float(s.meanh),
                        "best_gain": float(gain), "scale": scale,
                    })
        if not doagain:
            break
    net = np.vstack(s.netoutputs)
    return {
        "variant": asdict(v),
        "initial_harmony": initial_h.tolist(),
        "final": {
            "mean_harmony": float(s.meanh),
            "sum_harmony": float(np.sum(s.h)),
            "cv": float(s.stdh / abs(s.meanh)),
            "min_harmony": float(np.min(s.h)),
            "harmony": s.h.tolist(),
            "accepted_moves": accepted,
            "attempted_corrections": attempts,
            "iterations_counter": counter,
            "stop_reason": stop,
            "negative_net_output_cells": int(np.sum(net < 0.0)),
        },
        "trace": trace,
    }


def first_divergence(a: dict, b: dict, tol: float = 1e-12):
    if np.max(np.abs(np.asarray(a["initial_harmony"]) - np.asarray(b["initial_harmony"]))) > tol:
        return {"stage": "initial"}
    for i, (x, y) in enumerate(zip(a["trace"], b["trace"]), 1):
        if (x["destination_year"], x["source_year"], x["accepted"]) != (y["destination_year"], y["source_year"], y["accepted"]) or abs(x["mean_after"] - y["mean_after"]) > tol:
            return {
                "stage": "trace", "attempt_index": i,
                "baseline": {k: x.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
                "variant": {k: y.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
            }
    if len(a["trace"]) != len(b["trace"]):
        return {"stage": "trace_length", "baseline": len(a["trace"]), "variant": len(b["trace"])}
    return None


def main():
    results = {v.name: run(v) for v in VARIANTS}
    base = results["baseline_csvplan_jl"]
    oracle = legacy.run_default(False)
    os = oracle["scenario"]
    assert oracle["iterations"] == base["final"]["iterations_counter"]
    assert oracle["stop_reason"] == base["final"]["stop_reason"]
    np.testing.assert_allclose(os.h, base["final"]["harmony"], rtol=0.0, atol=3e-15)

    summary = {"baseline_oracle_check": "PASS", "baseline": base["final"], "variants": {}}
    for name, r in results.items():
        if name == "baseline_csvplan_jl":
            continue
        f, bf = r["final"], base["final"]
        summary["variants"][name] = {
            "first_divergence": first_divergence(base, r),
            "mean_harmony": f["mean_harmony"],
            "delta_mean_vs_baseline": f["mean_harmony"] - bf["mean_harmony"],
            "cv": f["cv"], "delta_cv_vs_baseline": f["cv"] - bf["cv"],
            "min_harmony": f["min_harmony"],
            "delta_min_vs_baseline": f["min_harmony"] - bf["min_harmony"],
            "accepted_moves": f["accepted_moves"],
            "attempted_corrections": f["attempted_corrections"],
            "iterations_counter": f["iterations_counter"],
            "stop_reason": f["stop_reason"],
            "negative_net_output_cells": f["negative_net_output_cells"],
        }

    d1 = results["D1_C11a_inverse_on_historical_latent_timing"]["final"]
    d2 = results["D2_C11b_inverse_on_exact_timing"]["final"]
    summary["C11b_exact_vs_latent_inverse"] = {
        "delta_mean": d2["mean_harmony"] - d1["mean_harmony"],
        "delta_cv": d2["cv"] - d1["cv"],
        "delta_min": d2["min_harmony"] - d1["min_harmony"],
    }

    (OUT / "depreciation_timing_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "depreciation_timing_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_DEPRECIATION_TIMING_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
