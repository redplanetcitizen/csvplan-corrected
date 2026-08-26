from __future__ import annotations

"""One-factor-at-a-time audit of direct csvplan.jl/text divergences.

This script never changes :mod:`csvplan_corrected.legacy`.  It reconstructs the
legacy execution with switches so that every run differs from Cockshott's
historical matrix prototype in exactly one local behaviour.
"""

from dataclasses import asdict, dataclass
import copy
import json
from pathlib import Path

import numpy as np

from csvplan_corrected import legacy


OUT = Path("comparison/stage_a")
OUT.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Variant:
    name: str
    vector_investment_subtraction: bool = False  # C13
    include_last_product_in_harmony: bool = False  # C02/C28
    post_candidate_positivity: bool = False  # C12
    inverse_depreciation: bool = False  # C11, enable latent matrix-code path
    exact_investment_stock_timing: bool = False  # C16 timing audit


VARIANTS = [
    Variant("baseline_csvplan_jl"),
    Variant("A1_C13_vector_investment_subtraction", vector_investment_subtraction=True),
    Variant("A2_C02_include_last_product", include_last_product_in_harmony=True),
    Variant("A3_C12_post_candidate_positivity", post_candidate_positivity=True),
    Variant("A4_C11_enable_existing_inverse_depreciation", inverse_depreciation=True),
    Variant("A5_C16_exact_investment_stock_timing", exact_investment_stock_timing=True),
]


def _depreciate_exact(amount: np.ndarray, periods: int, dep: np.ndarray) -> np.ndarray:
    """Direct implementation of surviving stock after ``periods`` full periods."""
    if periods < 0:
        raise ValueError("periods must be nonnegative")
    return np.asarray(amount, dtype=np.float64) * np.power(1.0 - dep, periods)


def _update_subsequent_capital(
    first_year_available: int,
    amount: np.ndarray,
    dep: np.ndarray,
    stock: np.ndarray,
    variant: Variant,
) -> None:
    if not variant.exact_investment_stock_timing:
        legacy.update_subsequent_years_capital(first_year_available, amount, dep, stock)
        return
    for year in range(first_year_available, stock.shape[0]):
        stock[year] += _depreciate_exact(amount, year - first_year_available, dep)


def _refresh_outputs(s: legacy.Scenario, variant: Variant) -> None:
    lastyear = s.prob.TheLastYear
    investments_by_type = legacy.investmentsByTypeandYear(s.investments)
    s.investmentsByTypeAndYear = investments_by_type
    s.targets = s.prob.g[:, :-1] + investments_by_type
    g_plus_i = np.zeros_like(s.prob.g, dtype=np.float64)
    g_plus_i[:, :-1] = s.targets
    s.O = np.vstack(
        [legacy.grossOutputForDemandf(g_plus_i[i, :], s.prob.A) for i in range(lastyear)]
    )
    legacy.compute_goal_fulfillment_scenario(s)
    ratios = s.goal_fullfilment_ratio_vector
    finaloutput = [s.targets[i, :] * ratios[i] for i in range(lastyear)]

    if variant.vector_investment_subtraction:
        s.netoutputs = [finaloutput[i] - investments_by_type[i, :] for i in range(lastyear)]
    else:
        inv_linear = investments_by_type.ravel(order="F")
        s.netoutputs = [finaloutput[i] - inv_linear[i] for i in range(lastyear)]


def _refresh_harmony(s: legacy.Scenario, variant: Variant) -> None:
    lastyear = s.prob.TheLastYear
    fulfillment = [s.netoutputs[i] / s.prob.g[i, :-1] for i in range(lastyear)]
    product_h = [legacy.harmony(fulfillment[i]) for i in range(lastyear)]
    if variant.include_last_product_in_harmony:
        annual = np.asarray([np.min(row) for row in product_h], dtype=np.float64)
    else:
        annual = np.asarray([np.min(row[:-1]) for row in product_h], dtype=np.float64)
    s.h = annual
    s.meanh = float(np.mean(annual))
    s.stdh = float(np.std(annual, ddof=1))


def _refresh(s: legacy.Scenario, variant: Variant) -> None:
    _refresh_outputs(s, variant)
    _refresh_harmony(s, variant)


def _update_scenario(
    s: legacy.Scenario,
    source_year: int,
    capital: np.ndarray,
    variant: Variant,
) -> legacy.Scenario:
    s.investments[source_year] += capital
    if float(np.sum(capital)) == 0.0:
        raise ValueError("attempt to update with zero investment")
    _update_subsequent_capital(source_year + 1, capital, s.prob.dep, s.si, variant)
    return s


def _candidate(
    s: legacy.Scenario,
    source_year: int,
    capital: np.ndarray,
    variant: Variant,
) -> legacy.Scenario:
    s2 = copy.deepcopy(s)
    _update_scenario(s2, source_year, capital, variant)
    _refresh(s2, variant)
    return s2


def _attempt_scale_up(
    s: legacy.Scenario,
    destination_year: int,
    scale_increment: float,
    variant: Variant,
):
    current_stock = s.si[destination_year]
    n, _ = current_stock.shape
    additional_capital = np.maximum(current_stock * scale_increment, 0.0)

    best_year = None
    best_gain = 0.0
    best_scenario = s
    candidate_rows = []

    for source_year in range(destination_year):
        source_capital = additional_capital
        if variant.inverse_depreciation:
            # This intentionally enables the *existing matrix-code call convention*
            # only.  It does not correct the separate timing ambiguity in C11/C16.
            source_capital = legacy.inversedepreciate(
                additional_capital,
                destination_year - 1 - source_year,
                s.prob.dep,
            )
        newscenario = _candidate(s, source_year, source_capital, variant)
        gain = float(newscenario.meanh - s.meanh)
        if variant.post_candidate_positivity:
            posflags = newscenario.netoutputs[source_year][:n] > np.zeros(n)
        else:
            posflags = s.netoutputs[source_year][:n] > np.zeros(n)
        feasible = bool(np.prod(posflags))
        candidate_rows.append(
            {
                "source_year": source_year,
                "gain": gain,
                "positivity_pass": feasible,
                "candidate_min_net_output_source": float(np.min(newscenario.netoutputs[source_year][:n])),
            }
        )
        if gain > best_gain and feasible:
            best_year = source_year
            best_gain = gain
            best_scenario = newscenario

    return best_scenario, best_year, best_gain, candidate_rows


def _build_initial(variant: Variant) -> legacy.Scenario:
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
        (problem.TheLastYear, problem.caprows, problem.capcols),
        dtype=np.float64,
    )
    preliminary = legacy.INITIAL_INVESTMENT_LEVEL * (problem.caps * problem.dep)
    for year in range(problem.TheLastYear - 1):
        investments[year] = preliminary
        _update_subsequent_capital(year + 1, preliminary, problem.dep, stock, variant)

    s = legacy.Scenario(
        problem,
        output,
        stock,
        investments,
        np.zeros(problem.TheLastYear, dtype=np.float64),
        np.zeros(problem.TheLastYear, dtype=np.float64),
        0.0,
        0.0,
        np.zeros((problem.TheLastYear, problem.capcols), dtype=np.float64),
        [np.zeros(problem.capcols, dtype=np.float64) for _ in range(problem.TheLastYear)],
        problem.g.copy(),
    )
    _refresh(s, variant)
    return s


def _run(variant: Variant) -> dict:
    s = _build_initial(variant)
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

            if s.h[destination_year] < s.meanh:
                attempted_corrections += 1
                target = legacy.harmonyInverse(s.meanh)
                current = legacy.harmonyInverse(s.h[destination_year])
                scale_increment = float((target - current) * legacy.EPSILON)
                before = s
                candidate, source_year, best_gain, candidates = _attempt_scale_up(
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
                    break
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
        "variant": asdict(variant),
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


def _first_divergence(baseline: dict, variant: dict, tol: float = 1e-12):
    if np.max(np.abs(np.asarray(baseline["initial"]["harmony"]) - np.asarray(variant["initial"]["harmony"]))) > tol:
        return {"stage": "initial_harmony"}
    btrace = baseline["trace"]
    vtrace = variant["trace"]
    for idx in range(min(len(btrace), len(vtrace))):
        b = btrace[idx]
        v = vtrace[idx]
        if (
            b["destination_year"] != v["destination_year"]
            or b["source_year"] != v["source_year"]
            or b["accepted"] != v["accepted"]
            or abs(b["mean_after"] - v["mean_after"]) > tol
        ):
            return {
                "stage": "trace",
                "accepted_attempt_index": idx + 1,
                "baseline": {k: b.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
                "variant": {k: v.get(k) for k in ("counter", "destination_year", "source_year", "accepted", "mean_after")},
            }
    if len(btrace) != len(vtrace):
        return {"stage": "trace_length", "baseline": len(btrace), "variant": len(vtrace)}
    return None


def main() -> None:
    results = {variant.name: _run(variant) for variant in VARIANTS}
    baseline = results["baseline_csvplan_jl"]

    # The switchable reconstruction must reproduce the already-verified oracle
    # exactly when every switch is off.
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
            "first_divergence": _first_divergence(baseline, result),
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
