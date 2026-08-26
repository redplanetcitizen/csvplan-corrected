from __future__ import annotations

"""Isolate C26: multi-good additional-capital update at the destination.

The audit holds the cumulative P3 state fixed:
  * C13/C02/C12 direct corrections;
  * exact source-to-destination depreciation and exact endogenous stock timing;
  * global-lowest destination;
  * historical 70% preliminary schedule and historical matrix epsilon;
  * historical first-blocked stop.

Only the matrix that represents *additional capital required at destination* is
changed.  The historical `current_stock * scale` rule is compared with two
explicit reconstructions.  Neither reconstruction is attributed to Cockshott;
the purpose is to determine whether C26 can safely remain an implementation
specialisation or materially changes the local-search path.
"""

from dataclasses import dataclass, asdict
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


COMP = Path(__file__).with_name("run_csvplan_composite_audit.py")
spec = importlib.util.spec_from_file_location("csvplan_composite_for_c26", COMP)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load composite audit helpers")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

OUT = Path("comparison/c26")
OUT.mkdir(parents=True, exist_ok=True)

BASE = m.Variant(
    "P3_C26_base",
    direct_defects=True,
    exact_depreciation=True,
    global_lowest=True,
    epsilon=legacy.EPSILON,
)


@dataclass(frozen=True)
class C26Variant:
    name: str
    capital_rule: str


def _scale_gap(s, dest):
    target_ratio = legacy.harmonyInverse(s.meanh)
    current_ratio = legacy.harmonyInverse(s.h[dest])
    scale = float((target_ratio - current_ratio) * BASE.epsilon)
    return current_ratio, target_ratio, scale


def _capital_historical(s, dest, scale):
    return np.maximum(s.si[dest] * scale, 0.0)


def _capital_incremental_coefficients(s, dest, scale):
    """Capital coefficients times the gross-output increment implied by scale.

    `scale` is an increment in the plan-ray fulfilment ratio.  The corresponding
    final-social-demand increment is g_t * scale.  Leontief maps it to gross
    output; C maps gross output to capital requirements.  This formulation does
    not credit slack already present in the destination stock.
    """
    p = s.prob
    n, mcap = s.si[dest].shape
    delta_final = np.zeros(p.A.shape[0], dtype=np.float64)
    delta_final[:n] = p.g[dest, :n] * scale
    delta_gross = legacy.grossOutputForDemandf(delta_final, p.A)
    required_increment = legacy.rowiseScale(p.C, delta_gross)
    return np.maximum(required_increment[:n, :mcap], 0.0)


def _capital_required_gap(s, dest, current_ratio, scale):
    """Gap between stock and capital required for the proposed destination ray.

    Existing destination-year investment remains in final demand.  Consumer
    final output is moved from the binding fulfilment ratio by `scale`; gross
    output is obtained by Leontief inversion, then translated to a cellwise
    capital requirement by C.  Existing stock slack is credited explicitly.
    """
    p = s.prob
    n, mcap = s.si[dest].shape
    desired_ratio = current_ratio + scale

    final_demand = np.zeros(p.A.shape[0], dtype=np.float64)
    final_demand[:n] = p.g[dest, :n] * desired_ratio
    # Keep the destination year's already scheduled accumulation in final demand.
    investment_by_type = legacy.investmentsByTypeandYear(s.investments)[dest]
    final_demand[:n] += investment_by_type[:n]

    desired_gross = legacy.grossOutputForDemandf(final_demand, p.A)
    required_total = legacy.rowiseScale(p.C, desired_gross)
    gap = required_total[:n, :mcap] - s.si[dest]
    return np.maximum(gap, 0.0)


def additional_at_destination(s, dest, v: C26Variant):
    current_ratio, target_ratio, scale = _scale_gap(s, dest)
    if v.capital_rule == "historical_stock_proportional":
        cap = _capital_historical(s, dest, scale)
    elif v.capital_rule == "coefficient_increment":
        cap = _capital_incremental_coefficients(s, dest, scale)
    elif v.capital_rule == "required_stock_gap":
        cap = _capital_required_gap(s, dest, current_ratio, scale)
    else:
        raise ValueError(v.capital_rule)
    return cap, current_ratio, target_ratio, scale


def attempt(s, dest, v: C26Variant):
    additional, current_ratio, target_ratio, scale = additional_at_destination(s, dest, v)
    n, _ = additional.shape
    best_source = None
    best_gain = 0.0
    best_scenario = s
    candidate_rows = []

    for source in range(dest):
        source_capital = m.exact_inverse(additional, source, dest, s.prob.dep)
        c = m.candidate(s, source, source_capital, BASE)
        gain = float(c.meanh - s.meanh)
        feasible = bool(np.prod(c.netoutputs[source][:n] > np.zeros(n)))
        candidate_rows.append({
            "source_year": source,
            "gain": gain,
            "candidate_positive": feasible,
            "destination_capital_total": float(np.sum(additional)),
            "source_capital_total": float(np.sum(source_capital)),
        })
        if gain > best_gain and feasible:
            best_source = source
            best_gain = gain
            best_scenario = c

    return best_scenario, best_source, best_gain, scale, current_ratio, target_ratio, candidate_rows


def run(v: C26Variant):
    s = m.build_initial(BASE)
    initial = {
        "mean_harmony": float(s.meanh),
        "cv": float(s.stdh / abs(s.meanh)),
        "min_harmony": float(np.min(s.h)),
        "harmony": s.h.tolist(),
    }
    trace = []
    counter = 1
    accepted = 0
    attempts = 0
    stop = None

    while True:
        cv = float(s.stdh / abs(s.meanh))
        if cv < legacy.MINCOEFF:
            stop = "cv"
            break
        if counter > legacy.MAXITER:
            stop = "maxiter"
            break

        dest = int(np.argmin(s.h))
        counter += 1
        attempts += 1
        before = float(s.meanh)
        c, source, gain, scale, current_ratio, target_ratio, candidates = attempt(s, dest, v)
        if source is None:
            stop = "no_transfer"
            trace.append({
                "counter": counter,
                "destination_year": dest,
                "source_year": None,
                "accepted": False,
                "mean_before": before,
                "mean_after": before,
                "scale": scale,
                "current_ratio": current_ratio,
                "mean_target_ratio": target_ratio,
                "candidates": candidates,
            })
            break

        s = c
        accepted += 1
        trace.append({
            "counter": counter,
            "destination_year": dest,
            "source_year": int(source),
            "accepted": True,
            "mean_before": before,
            "mean_after": float(s.meanh),
            "best_gain": float(gain),
            "scale": scale,
            "current_ratio": current_ratio,
            "mean_target_ratio": target_ratio,
        })

    net = np.vstack(s.netoutputs)
    final = {
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
        "min_net_output": float(np.min(net)),
    }
    return {"variant": asdict(v), "initial": initial, "final": final, "trace": trace}


def first_divergence(a, b, tol=1e-12):
    for i, (x, y) in enumerate(zip(a["trace"], b["trace"]), 1):
        keys = ("destination_year", "source_year", "accepted")
        if tuple(x.get(k) for k in keys) != tuple(y.get(k) for k in keys) or abs(x["mean_after"] - y["mean_after"]) > tol:
            return {
                "attempt_index": i,
                "historical": {k: x.get(k) for k in ("destination_year", "source_year", "accepted", "mean_after", "scale")},
                "variant": {k: y.get(k) for k in ("destination_year", "source_year", "accepted", "mean_after", "scale")},
            }
    if len(a["trace"]) != len(b["trace"]):
        return {"trace_length": [len(a["trace"]), len(b["trace"])]}
    return None


def main():
    variants = [
        C26Variant("C26_historical_stock_proportional", "historical_stock_proportional"),
        C26Variant("C26_coefficient_increment", "coefficient_increment"),
        C26Variant("C26_required_stock_gap", "required_stock_gap"),
    ]
    results = {v.name: run(v) for v in variants}
    base = results[variants[0].name]

    # The historical-stock rule here must reproduce P3 exactly.
    p3 = m.run(BASE)
    np.testing.assert_allclose(
        results[variants[0].name]["final"]["harmony"],
        p3["final"]["harmony"],
        rtol=0.0,
        atol=1e-12,
    )

    summary = {
        "p3_oracle_check": "PASS",
        "source_status": "C26 remains indeterminate: only historical formula is executable evidence; alternatives are reconstructions",
        "variants": {},
    }
    for v in variants:
        r = results[v.name]
        f = r["final"]
        summary["variants"][v.name] = {
            "capital_rule": v.capital_rule,
            "first_divergence_from_historical": first_divergence(base, r) if v is not variants[0] else None,
            "mean_harmony": f["mean_harmony"],
            "delta_mean_vs_historical": f["mean_harmony"] - base["final"]["mean_harmony"],
            "cv": f["cv"],
            "delta_cv_vs_historical": f["cv"] - base["final"]["cv"],
            "min_harmony": f["min_harmony"],
            "delta_min_vs_historical": f["min_harmony"] - base["final"]["min_harmony"],
            "accepted_moves": f["accepted_moves"],
            "attempted_corrections": f["attempted_corrections"],
            "stop_reason": f["stop_reason"],
            "negative_net_output_cells": f["negative_net_output_cells"],
        }

    (OUT / "c26_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "c26_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_C26_AUDIT_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
