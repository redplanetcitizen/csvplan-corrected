from __future__ import annotations

"""Audit residual code-only choices on top of the P3 reconciled candidate.

P3 means: confirmed vector/indexing/constraint corrections, exact endogenous
source-to-destination depreciation, global-lowest destination rule, historical
matrix epsilon.  This script does not alter ``legacy.py`` or declare a canonical
replacement.  It isolates the remaining code-only choices:

C14 preliminary replacement schedule (level, scope, and stock timing),
C21 shadow-horizon target/labour continuation sensitivity,
C23/C24 first-blocked stopping versus ranked fallback,
C29 stopping threshold and maximum-iteration parameterisation.
"""

from dataclasses import dataclass, asdict
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


COMP = Path(__file__).with_name("run_csvplan_composite_audit.py")
spec = importlib.util.spec_from_file_location("csvplan_composite_for_residual", COMP)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load composite audit helpers")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

OUT = Path("comparison/residual_code_only")
OUT.mkdir(parents=True, exist_ok=True)

BASE = m.Variant(
    "P3_base",
    direct_defects=True,
    exact_depreciation=True,
    global_lowest=True,
    epsilon=legacy.EPSILON,
)


@dataclass(frozen=True)
class ResidualVariant:
    name: str
    preliminary_level: float = 0.7
    preliminary_scope: str = "all"          # all | published | shadow | none
    preliminary_timing: str = "historical" # historical | exact
    shadow_target_scale: float = 1.0
    shadow_labour_scale: float = 1.0
    stop_mode: str = "first_blocked"        # first_blocked | ranked_fallback
    mincoeff: float = legacy.MINCOEFF
    maxiter: int = legacy.MAXITER


def _published_horizon(p) -> int:
    return p.TheLastYear - legacy.DEPRECIATION_HORIZON


def _scope_accepts(scope: str, year: int, published_horizon: int) -> bool:
    if scope == "all":
        return True
    if scope == "none":
        return False
    if scope == "published":
        return year < published_horizon
    if scope == "shadow":
        return year >= published_horizon
    raise ValueError(f"unknown preliminary_scope {scope}")


def _add_preliminary_exact(year: int, investments, amount, dep, stock) -> None:
    investments[year] = amount
    first_available = year + 1
    for dest in range(first_available, stock.shape[0]):
        stock[dest] += amount * np.power(1.0 - dep, dest - first_available)


def build_initial(v: ResidualVariant):
    p = legacy.readInProblem(*legacy.default_data_paths())
    pub = _published_horizon(p)

    # C21 sensitivity only: perturb *shadow* continuation rows, leaving the
    # published plan untouched.  The terminal computational target is then
    # recomputed exactly as in csvplan.
    if pub < p.TheLastYear:
        p.g[pub:, :-1] *= v.shadow_target_scale
        p.labouravailable[pub:] *= v.shadow_labour_scale

    _, lastgoal = legacy.For_the_last_year_of_the_plan_return_a_net_output_target(
        p.TheLastYear - 1, p.A, p.D, p.g, p.labouravailable
    )
    p.g[p.TheLastYear - 1, :] = lastgoal

    O = np.vstack([legacy.grossOutputForDemandf(p.g[i, :], p.A) for i in range(p.TheLastYear)])
    stock = legacy.Assign_to_each_year_capital_stock(p.caps, p.dep, p.TheLastYear)
    investments = np.zeros((p.TheLastYear, p.caprows, p.capcols), dtype=np.float64)
    prelim = v.preliminary_level * (p.caps * p.dep)

    for y in range(p.TheLastYear - 1):
        if not _scope_accepts(v.preliminary_scope, y, pub):
            continue
        if v.preliminary_timing == "historical":
            legacy.setup_preliminary_investment_schedule(y, investments, prelim, p.dep, stock)
        elif v.preliminary_timing == "exact":
            _add_preliminary_exact(y, investments, prelim, p.dep, stock)
        else:
            raise ValueError(f"unknown preliminary_timing {v.preliminary_timing}")

    s = legacy.Scenario(
        p, O, stock, investments,
        np.zeros(p.TheLastYear), np.zeros(p.TheLastYear), 0.0, 0.0,
        np.zeros((p.TheLastYear, p.capcols)),
        [np.zeros(p.capcols) for _ in range(p.TheLastYear)],
        p.g.copy(),
    )
    m.a._refresh(s, m.avar(BASE))
    return s, pub


def _attempt(s, dest):
    return m.attempt(s, dest, BASE)


def run_controller(s, v: ResidualVariant):
    trace = []
    counter = 1
    accepted = 0
    attempts = 0
    stop = None

    while True:
        cv = float(s.stdh / abs(s.meanh))
        if cv < v.mincoeff:
            stop = "cv"
            break
        if counter > v.maxiter:
            stop = "maxiter"
            break

        if v.stop_mode == "first_blocked":
            destinations = [int(np.argmin(s.h))]
        elif v.stop_mode == "ranked_fallback":
            destinations = [int(i) for i in np.argsort(s.h)]
        else:
            raise ValueError(f"unknown stop_mode {v.stop_mode}")

        moved = False
        blocked = []
        for dest in destinations:
            # There is no preceding source for year zero.  Under first-blocked
            # this terminates; under fallback it is recorded and the next-lowest
            # feasible destination is tried.
            if dest == 0:
                blocked.append({"destination_year": dest, "reason": "no_previous_source"})
                if v.stop_mode == "first_blocked":
                    stop = "no_transfer"
                    break
                continue

            attempts += 1
            counter += 1
            before = float(s.meanh)
            c, source, gain, scale, candidates = _attempt(s, dest)
            if source is None:
                blocked.append({
                    "destination_year": dest,
                    "reason": "no_positive_source",
                    "scale": scale,
                    "candidates": candidates,
                })
                if v.stop_mode == "first_blocked":
                    stop = "no_transfer"
                    trace.append({
                        "counter": counter, "destination_year": dest,
                        "source_year": None, "accepted": False,
                        "mean_before": before, "mean_after": before,
                        "blocked": blocked,
                    })
                    break
                continue

            s = c
            accepted += 1
            moved = True
            trace.append({
                "counter": counter, "destination_year": dest,
                "source_year": int(source), "accepted": True,
                "mean_before": before, "mean_after": float(s.meanh),
                "best_gain": float(gain), "scale": scale,
                "blocked_before_move": blocked,
            })
            break

        if stop is not None:
            break
        if not moved:
            stop = "no_transfer_full_pass"
            trace.append({
                "counter": counter, "destination_year": None,
                "source_year": None, "accepted": False,
                "mean_before": float(s.meanh), "mean_after": float(s.meanh),
                "blocked": blocked,
            })
            break

    return s, trace, counter, accepted, attempts, stop


def metrics(s, pub):
    net = np.vstack(s.netoutputs)
    full_h = np.asarray(s.h)
    pub_h = full_h[:pub]
    preliminary_total = float(np.sum(s.investments))
    return {
        "mean_harmony": float(np.mean(full_h)),
        "sum_harmony": float(np.sum(full_h)),
        "cv": float(np.std(full_h, ddof=1) / abs(np.mean(full_h))),
        "min_harmony": float(np.min(full_h)),
        "published_mean_harmony": float(np.mean(pub_h)),
        "published_cv": float(np.std(pub_h, ddof=1) / abs(np.mean(pub_h))) if pub > 1 else 0.0,
        "published_min_harmony": float(np.min(pub_h)),
        "negative_net_output_cells": int(np.sum(net < 0.0)),
        "min_net_output": float(np.min(net)),
        "investment_total": preliminary_total,
    }


def run(v: ResidualVariant):
    s, pub = build_initial(v)
    initial = metrics(s, pub)
    initial_investment_total = float(np.sum(s.investments))
    s, trace, counter, accepted, attempts, stop = run_controller(s, v)
    final = metrics(s, pub)
    final.update({
        "accepted_moves": accepted,
        "attempted_corrections": attempts,
        "iterations_counter": counter,
        "stop_reason": stop,
        "published_horizon": pub,
        "computational_horizon": s.prob.TheLastYear,
        "initial_preliminary_investment_total": initial_investment_total,
    })
    return {"variant": asdict(v), "initial": initial, "final": final, "trace": trace}


def _compact(r):
    f = r["final"]
    return {
        "mean_harmony": f["mean_harmony"],
        "cv": f["cv"],
        "min_harmony": f["min_harmony"],
        "published_mean_harmony": f["published_mean_harmony"],
        "published_cv": f["published_cv"],
        "published_min_harmony": f["published_min_harmony"],
        "accepted_moves": f["accepted_moves"],
        "attempted_corrections": f["attempted_corrections"],
        "iterations_counter": f["iterations_counter"],
        "stop_reason": f["stop_reason"],
        "initial_preliminary_investment_total": f["initial_preliminary_investment_total"],
        "negative_net_output_cells": f["negative_net_output_cells"],
    }


def main():
    results = {}

    # C14 level sweep: dense enough to determine whether 0.70 is a sharp
    # requirement or merely one point in a broad basin.
    sweep_levels = [round(x, 2) for x in np.arange(0.0, 1.51, 0.1)]
    if 0.7 not in sweep_levels:
        sweep_levels.append(0.7)
    for level in sorted(set(sweep_levels)):
        v = ResidualVariant(f"C14_level_{level:.2f}", preliminary_level=level)
        results[v.name] = run(v)

    # C14 scope: identify whether the preliminary schedule mainly regularises
    # the published years, the shadow years, or both.
    for scope in ("none", "published", "shadow", "all"):
        v = ResidualVariant(f"C14_scope_{scope}", preliminary_level=0.7, preliminary_scope=scope)
        results[v.name] = run(v)

    # C14/C16 interaction: if the preliminary schedule is retained, test the
    # same exact stock timing used for endogenous investment in P3.
    for timing in ("historical", "exact"):
        v = ResidualVariant(f"C14_timing_{timing}", preliminary_level=0.7, preliminary_timing=timing)
        results[v.name] = run(v)

    # C23/C24: does the globally worst year block improvements elsewhere?
    for stop_mode in ("first_blocked", "ranked_fallback"):
        v = ResidualVariant(f"C24_stop_{stop_mode}", stop_mode=stop_mode)
        results[v.name] = run(v)

    # C29: scalar and matrix thresholds / iteration caps plus one deliberately
    # loose threshold to demonstrate when the parameter becomes binding.
    for mincoeff, maxiter, label in (
        (0.01, 3000, "threshold_001"),
        (0.034, 3000, "threshold_0034"),
        (0.05, 3000, "threshold_005"),
        (0.034, 500, "maxiter_500"),
    ):
        v = ResidualVariant(f"C29_{label}", mincoeff=mincoeff, maxiter=maxiter)
        results[v.name] = run(v)

    # C21: sensitivity only, not authorial adjudication.  Perturb shadow rows
    # by +/-10% while published rows remain unchanged.
    for ts, ls, label in (
        (0.9, 1.0, "targets_minus10"),
        (1.1, 1.0, "targets_plus10"),
        (1.0, 0.9, "labour_minus10"),
        (1.0, 1.1, "labour_plus10"),
        (0.9, 0.9, "both_minus10"),
        (1.1, 1.1, "both_plus10"),
    ):
        v = ResidualVariant(f"C21_{label}", shadow_target_scale=ts, shadow_labour_scale=ls)
        results[v.name] = run(v)

    baseline = results["C14_level_0.70"]
    bf = baseline["final"]

    # Determine Pareto dominance against the historical 70% P3 point on the
    # three agreed full-horizon metrics.  Higher mean/min and lower CV are better.
    sweep_summary = []
    for level in sorted(set(sweep_levels)):
        r = results[f"C14_level_{level:.2f}"]
        f = r["final"]
        dominates_70 = (
            f["mean_harmony"] >= bf["mean_harmony"]
            and f["min_harmony"] >= bf["min_harmony"]
            and f["cv"] <= bf["cv"]
            and (
                f["mean_harmony"] > bf["mean_harmony"]
                or f["min_harmony"] > bf["min_harmony"]
                or f["cv"] < bf["cv"]
            )
        )
        sweep_summary.append({"level": level, **_compact(r), "dominates_0_70": dominates_70})

    best_mean = max(sweep_summary, key=lambda x: x["mean_harmony"])
    best_min = max(sweep_summary, key=lambda x: x["min_harmony"])
    best_cv = min(sweep_summary, key=lambda x: x["cv"])

    summary = {
        "base_definition": "P3 + historical epsilon; only residual code-only knobs varied",
        "baseline_0_70": _compact(baseline),
        "C14_level_sweep": sweep_summary,
        "C14_best_by_metric": {"mean": best_mean, "min": best_min, "cv": best_cv},
        "C14_scope": {k: _compact(v) for k, v in results.items() if k.startswith("C14_scope_")},
        "C14_timing": {k: _compact(v) for k, v in results.items() if k.startswith("C14_timing_")},
        "C24_stop": {k: _compact(v) for k, v in results.items() if k.startswith("C24_stop_")},
        "C29_parameters": {k: _compact(v) for k, v in results.items() if k.startswith("C29_")},
        "C21_shadow_sensitivity": {k: _compact(v) for k, v in results.items() if k.startswith("C21_")},
    }

    (OUT / "residual_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "residual_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_RESIDUAL_CODE_ONLY_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
