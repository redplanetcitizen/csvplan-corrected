from __future__ import annotations

"""Staged interaction audit for csvplan.

This script does not define a canonical replacement.  It adds source-supported
changes in a controlled sequence so their interaction can be measured while
ambiguous historical choices (70% preliminary schedule, historical epsilon and
historical stop semantics) remain fixed until the optional final tuning run.
"""

from dataclasses import dataclass, asdict
import copy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


A_PATH = Path(__file__).with_name("run_csvplan_stage_a.py")
spec = importlib.util.spec_from_file_location("csvplan_stage_a_for_composite", A_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Stage A helpers")
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)

OUT = Path("comparison/composite")
OUT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Variant:
    name: str
    direct_defects: bool = False       # C13 + C02 + C12
    exact_depreciation: bool = False   # C11a + C11b + endogenous C16
    global_lowest: bool = False        # C05
    epsilon: float = legacy.EPSILON


TEXT_EPSILON = 1.0 / (1.0 + legacy.DEPRECIATION_HORIZON)
VARIANTS = [
    Variant("P0_historical_csvplan_jl"),
    Variant("P1_confirmed_indexing_constraint_defects", direct_defects=True),
    Variant("P2_P1_plus_exact_depreciation", direct_defects=True, exact_depreciation=True),
    Variant("P3_P2_plus_global_lowest", direct_defects=True, exact_depreciation=True, global_lowest=True),
    Variant("P4_P3_plus_text_first_suggestion_epsilon", direct_defects=True, exact_depreciation=True, global_lowest=True, epsilon=TEXT_EPSILON),
]


def avar(v: Variant):
    return a.Variant(
        v.name,
        vector_investment_subtraction=v.direct_defects,
        include_last_product_in_harmony=v.direct_defects,
        post_candidate_positivity=v.direct_defects,
        inverse_depreciation=False,
        exact_investment_stock_timing=False,
    )


def build_initial(v: Variant):
    p = legacy.readInProblem(*legacy.default_data_paths())
    _, lastgoal = legacy.For_the_last_year_of_the_plan_return_a_net_output_target(
        p.TheLastYear - 1, p.A, p.D, p.g, p.labouravailable
    )
    p.g[p.TheLastYear - 1, :] = lastgoal
    O = np.vstack([legacy.grossOutputForDemandf(p.g[i, :], p.A) for i in range(p.TheLastYear)])
    stock = legacy.Assign_to_each_year_capital_stock(p.caps, p.dep, p.TheLastYear)
    investments = np.zeros((p.TheLastYear, p.caprows, p.capcols), dtype=np.float64)
    prelim = legacy.INITIAL_INVESTMENT_LEVEL * (p.caps * p.dep)
    # Keep C14 and its historical propagation fixed in every composite run.
    for y in range(p.TheLastYear - 1):
        legacy.setup_preliminary_investment_schedule(y, investments, prelim, p.dep, stock)
    s = legacy.Scenario(
        p, O, stock, investments,
        np.zeros(p.TheLastYear), np.zeros(p.TheLastYear), 0.0, 0.0,
        np.zeros((p.TheLastYear, p.capcols)),
        [np.zeros(p.capcols) for _ in range(p.TheLastYear)],
        p.g.copy(),
    )
    a._refresh(s, avar(v))
    return s


def exact_inverse(arrival, source, dest, dep):
    periods = dest - source - 1
    survival = np.power(1.0 - dep, periods)
    if np.any(survival <= 0.0):
        raise ValueError("non-positive survival")
    return arrival / survival


def candidate(s, source, capital, v: Variant):
    s2 = copy.deepcopy(s)
    s2.investments[source] += capital
    if v.exact_depreciation:
        first_available = source + 1
        for y in range(first_available, s2.prob.TheLastYear):
            periods = y - first_available
            s2.si[y] += capital * np.power(1.0 - s2.prob.dep, periods)
    else:
        legacy.update_subsequent_years_capital(source + 1, capital, s2.prob.dep, s2.si)
    a._refresh(s2, avar(v))
    return s2


def attempt(s, dest, v: Variant):
    target = legacy.harmonyInverse(s.meanh)
    current = legacy.harmonyInverse(s.h[dest])
    scale = float((target - current) * v.epsilon)
    additional_at_dest = np.maximum(s.si[dest] * scale, 0.0)
    n, _ = additional_at_dest.shape
    best_source = None
    best_gain = 0.0
    best_scenario = s
    candidates = []
    for source in range(dest):
        source_capital = (
            exact_inverse(additional_at_dest, source, dest, s.prob.dep)
            if v.exact_depreciation else additional_at_dest
        )
        c = candidate(s, source, source_capital, v)
        gain = float(c.meanh - s.meanh)
        positivity_state = c if v.direct_defects else s
        feasible = bool(np.prod(positivity_state.netoutputs[source][:n] > np.zeros(n)))
        candidates.append({
            "source_year": source, "gain": gain, "positivity_pass": feasible,
            "source_capital_total": float(np.sum(source_capital)),
        })
        if gain > best_gain and feasible:
            best_source = source
            best_gain = gain
            best_scenario = c
    return best_scenario, best_source, best_gain, scale, candidates


def run_sequential(s, v: Variant):
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
                c, source, gain, scale, candidates = attempt(s, dest, v)
                if source is None:
                    stop = "no_transfer"
                    doagain = False
                    trace.append({
                        "counter": counter, "destination_year": dest, "source_year": None,
                        "accepted": False, "mean_before": before, "mean_after": before,
                        "best_gain": 0.0, "scale": scale, "candidates": candidates,
                    })
                else:
                    s = c; accepted += 1
                    trace.append({
                        "counter": counter, "destination_year": dest, "source_year": int(source),
                        "accepted": True, "mean_before": before, "mean_after": float(s.meanh),
                        "best_gain": float(gain), "scale": scale,
                    })
        if not doagain:
            break
    return s, trace, counter, accepted, attempts, stop


def run_global(s, v: Variant):
    trace = []
    counter = 1
    accepted = 0
    attempts = 0
    stop = None
    while True:
        cv = float(s.stdh / abs(s.meanh))
        if cv < legacy.MINCOEFF:
            stop = "cv"; break
        if counter > legacy.MAXITER:
            stop = "maxiter"; break
        dest = int(np.argmin(s.h))
        counter += 1; attempts += 1
        before = float(s.meanh)
        c, source, gain, scale, candidates = attempt(s, dest, v)
        if source is None:
            stop = "no_transfer"
            trace.append({
                "counter": counter, "destination_year": dest, "source_year": None,
                "accepted": False, "mean_before": before, "mean_after": before,
                "best_gain": 0.0, "scale": scale, "candidates": candidates,
            })
            break
        s = c; accepted += 1
        trace.append({
            "counter": counter, "destination_year": dest, "source_year": int(source),
            "accepted": True, "mean_before": before, "mean_after": float(s.meanh),
            "best_gain": float(gain), "scale": scale,
        })
    return s, trace, counter, accepted, attempts, stop


def run(v: Variant):
    s = build_initial(v)
    initial = {
        "mean_harmony": float(s.meanh), "cv": float(s.stdh / abs(s.meanh)),
        "min_harmony": float(np.min(s.h)), "harmony": s.h.tolist(),
    }
    if v.global_lowest:
        s, trace, counter, accepted, attempts, stop = run_global(s, v)
    else:
        s, trace, counter, accepted, attempts, stop = run_sequential(s, v)
    net = np.vstack(s.netoutputs)
    return {
        "variant": asdict(v), "initial": initial,
        "final": {
            "mean_harmony": float(s.meanh), "sum_harmony": float(np.sum(s.h)),
            "cv": float(s.stdh / abs(s.meanh)), "min_harmony": float(np.min(s.h)),
            "harmony": s.h.tolist(), "accepted_moves": accepted,
            "attempted_corrections": attempts, "iterations_counter": counter,
            "stop_reason": stop, "negative_net_output_cells": int(np.sum(net < 0.0)),
            "min_net_output": float(np.min(net)),
        },
        "trace": trace,
    }


def first_divergence(x, y, tol=1e-12):
    if np.max(np.abs(np.asarray(x["initial"]["harmony"]) - np.asarray(y["initial"]["harmony"]))) > tol:
        return {"stage": "initial_harmony"}
    for i, (a0, b0) in enumerate(zip(x["trace"], y["trace"]), 1):
        if (a0["destination_year"], a0["source_year"], a0["accepted"]) != (b0["destination_year"], b0["source_year"], b0["accepted"]) or abs(a0["mean_after"] - b0["mean_after"]) > tol:
            return {"stage": "trace", "attempt_index": i,
                    "from": {k:a0.get(k) for k in ("counter","destination_year","source_year","accepted","mean_after")},
                    "to": {k:b0.get(k) for k in ("counter","destination_year","source_year","accepted","mean_after")}}
    if len(x["trace"]) != len(y["trace"]):
        return {"stage":"trace_length","from":len(x["trace"]),"to":len(y["trace"])}
    return None


def main():
    results = {v.name: run(v) for v in VARIANTS}
    p0 = results["P0_historical_csvplan_jl"]
    oracle = legacy.run_default(False); os = oracle["scenario"]
    assert oracle["iterations"] == p0["final"]["iterations_counter"]
    assert oracle["stop_reason"] == p0["final"]["stop_reason"]
    np.testing.assert_allclose(os.h, p0["final"]["harmony"], rtol=0.0, atol=3e-15)

    names = [v.name for v in VARIANTS]
    summary = {"baseline_oracle_check":"PASS", "text_epsilon":TEXT_EPSILON, "stages":{}}
    for i, name in enumerate(names):
        r = results[name]; f = r["final"]
        prev = results[names[i-1]] if i else None
        summary["stages"][name] = {
            "first_divergence_from_previous": first_divergence(prev, r) if prev else None,
            "initial_mean_harmony": r["initial"]["mean_harmony"],
            "mean_harmony": f["mean_harmony"], "sum_harmony": f["sum_harmony"],
            "cv": f["cv"], "min_harmony": f["min_harmony"],
            "accepted_moves": f["accepted_moves"], "attempted_corrections": f["attempted_corrections"],
            "iterations_counter": f["iterations_counter"], "stop_reason": f["stop_reason"],
            "negative_net_output_cells": f["negative_net_output_cells"],
        }
        if prev:
            pf = prev["final"]
            summary["stages"][name].update({
                "delta_mean_from_previous": f["mean_harmony"]-pf["mean_harmony"],
                "delta_cv_from_previous": f["cv"]-pf["cv"],
                "delta_min_from_previous": f["min_harmony"]-pf["min_harmony"],
            })

    (OUT/"composite_full.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    (OUT/"composite_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print("CSVPLAN_COMPOSITE_AUDIT_SUMMARY")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()
