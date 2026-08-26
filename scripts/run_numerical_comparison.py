from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from csvplan_corrected import faithful, legacy


OUT = Path("comparison")
OUT.mkdir(exist_ok=True)


def _legacy_attempt_with_trace(s: legacy.Scenario, destyear: int, scaleincrement: float):
    csy = s.si[destyear, :, :]
    n, _ = csy.shape
    additionalcapital = csy * scaleincrement
    additionalcapital = np.where(additionalcapital < 0.0, 0.0, additionalcapital)

    bestyear = None
    bestgain = 0.0
    bestscenario = s
    candidates = []
    for y in range(destyear):
        originalcapital = additionalcapital
        if legacy.INVERSE_DEPRECIATE_INVESTMENTS:
            originalcapital = legacy.inversedepreciate(
                additionalcapital, destyear - 1 - y, s.prob.dep
            )
        gain, newscenario = legacy.gainfromInvesting(s, y, originalcapital)
        posflags = s.netoutputs[y][:n] > np.zeros(n)
        feasible = bool(np.prod(posflags))
        candidates.append(
            {
                "source_year": y,
                "gain": float(gain),
                "feasible_precheck": feasible,
                "mean_after": float(newscenario.meanh),
            }
        )
        if gain > bestgain and feasible:
            bestyear = y
            bestgain = float(gain)
            bestscenario = newscenario

    return bestscenario, bestyear, bestgain, candidates


def run_legacy_trace():
    paths = legacy.default_data_paths()
    problem = legacy.readInProblem(*paths)

    _, lastgoal = legacy.For_the_last_year_of_the_plan_return_a_net_output_target(
        problem.TheLastYear - 1,
        problem.A,
        problem.D,
        problem.g,
        problem.labouravailable,
    )
    problem.g[problem.TheLastYear - 1, :] = lastgoal

    Otmp = np.vstack(
        [legacy.grossOutputForDemandf(problem.g[i, :], problem.A) for i in range(problem.TheLastYear)]
    )
    sitmp = legacy.Assign_to_each_year_capital_stock(
        problem.caps, problem.dep, problem.TheLastYear
    )
    investmentstmp = np.zeros(
        (problem.TheLastYear, problem.caprows, problem.capcols), dtype=np.float64
    )
    preassignedcapital = legacy.INITIAL_INVESTMENT_LEVEL * (problem.caps * problem.dep)
    for y in range(problem.TheLastYear - 1):
        legacy.setup_preliminary_investment_schedule(
            y, investmentstmp, preassignedcapital, problem.dep, sitmp
        )

    s = legacy.Scenario(
        problem,
        Otmp,
        sitmp,
        investmentstmp,
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

    initial = {
        "mean": float(s.meanh),
        "std": float(s.stdh),
        "h": s.h.tolist(),
    }
    trace = []
    iter_count = 1
    stop_reason = None
    doagain = True
    while doagain:
        for i in range(1, problem.TheLastYear):
            cv_abs = s.stdh / abs(s.meanh)
            if cv_abs < legacy.MINCOEFF or iter_count > legacy.MAXITER:
                stop_reason = "cv" if cv_abs < legacy.MINCOEFF else "maxiter"
                doagain = False
                break
            iter_count += 1
            if s.h[i] < s.meanh:
                upscale = legacy.Estimate_how_much__production_to_be_scaled_up(s, i)
                before_mean = float(s.meanh)
                before_h = s.h.copy()
                candidate, bestyear, bestgain, candidates = _legacy_attempt_with_trace(s, i, upscale)
                if bestyear is None:
                    stop_reason = "no_transfer"
                    doagain = False
                    trace.append(
                        {
                            "iteration": iter_count,
                            "destination_year": i,
                            "source_year": None,
                            "accepted": False,
                            "upscale": float(upscale),
                            "mean_before": before_mean,
                            "mean_after": before_mean,
                            "best_gain": 0.0,
                            "h_before": before_h.tolist(),
                            "h_after": before_h.tolist(),
                            "candidates": candidates,
                        }
                    )
                    break
                s = candidate
                trace.append(
                    {
                        "iteration": iter_count,
                        "destination_year": i,
                        "source_year": int(bestyear),
                        "accepted": True,
                        "upscale": float(upscale),
                        "mean_before": before_mean,
                        "mean_after": float(s.meanh),
                        "best_gain": float(bestgain),
                        "h_before": before_h.tolist(),
                        "h_after": s.h.tolist(),
                        "candidates": candidates,
                    }
                )
        if not doagain:
            break

    return {
        "problem": problem,
        "scenario": s,
        "initial": initial,
        "trace": trace,
        "iterations": iter_count,
        "stop_reason": stop_reason,
        "coefficient_of_variation": float(s.stdh / abs(s.meanh)),
    }


def main():
    faithful_result = faithful.run_default()
    legacy_trace = run_legacy_trace()

    f = faithful_result["scenario"]
    l = legacy_trace["scenario"]
    years = min(f.prob.horizon, l.prob.TheLastYear)
    legacy_net = np.vstack(l.netoutputs[:years])
    faithful_net = f.net_output[:years]

    summary = {
        "faithful": {
            "published_horizon": faithful_result["published_horizon"],
            "computational_horizon": faithful_result["computational_horizon"],
            "epsilon": faithful_result["epsilon"],
            "accepted_moves": faithful_result["iterations"],
            "attempts": faithful_result["attempts"],
            "stop_reason": faithful_result["stop_reason"],
            "mean_harmony": float(f.meanh),
            "std_harmony": float(f.stdh),
            "cv": float(faithful_result["coefficient_of_variation"]),
            "objective_sum_harmony": float(f.objective),
        },
        "legacy": {
            "computational_horizon": int(l.prob.TheLastYear),
            "epsilon": float(legacy.EPSILON),
            "accepted_moves": int(sum(1 for row in legacy_trace["trace"] if row["accepted"])),
            "iterations_counter": int(legacy_trace["iterations"]),
            "stop_reason": legacy_trace["stop_reason"],
            "initial_mean_harmony": legacy_trace["initial"]["mean"],
            "initial_std_harmony": legacy_trace["initial"]["std"],
            "mean_harmony": float(l.meanh),
            "std_harmony": float(l.stdh),
            "cv": float(legacy_trace["coefficient_of_variation"]),
            "sum_harmony": float(np.sum(l.h)),
        },
        "faithful_vs_legacy": {
            "max_abs_harmony_difference_all_years": float(np.max(np.abs(f.h[:years] - l.h[:years]))),
            "mean_abs_harmony_difference_all_years": float(np.mean(np.abs(f.h[:years] - l.h[:years]))),
            "max_abs_net_output_difference": float(np.max(np.abs(faithful_net - legacy_net))),
            "mean_harmony_difference": float(f.meanh - l.meanh),
            "cv_difference": float(faithful_result["coefficient_of_variation"] - legacy_trace["coefficient_of_variation"]),
        },
    }

    with (OUT / "python_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    with (OUT / "legacy_initial.json").open("w", encoding="utf-8") as fh:
        json.dump(legacy_trace["initial"], fh, indent=2)

    with (OUT / "legacy_trace.json").open("w", encoding="utf-8") as fh:
        json.dump(legacy_trace["trace"], fh, indent=2)

    with (OUT / "faithful_trace.json").open("w", encoding="utf-8") as fh:
        json.dump(faithful_result["accepted_steps"], fh, indent=2)

    with (OUT / "year_comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "year_index",
                "faithful_harmony",
                "legacy_harmony",
                "harmony_difference",
                "faithful_goal_scale",
                "legacy_goal_scale",
                "faithful_investment_total",
                "legacy_investment_total",
            ]
        )
        legacy_investment_totals = legacy.investmentsByTypeandYear(l.investments).sum(axis=1)
        for y in range(years):
            writer.writerow(
                [
                    y + 1,
                    f.h[y],
                    l.h[y],
                    f.h[y] - l.h[y],
                    f.lambdas[y],
                    l.goal_fullfilment_ratio_vector[y],
                    float(np.sum(f.I[y])),
                    float(legacy_investment_totals[y]),
                ]
            )

    print("PYTHON_COMPARISON_SUMMARY")
    print(json.dumps(summary, indent=2))
    print("LEGACY_TRACE_FIRST_3")
    print(json.dumps(legacy_trace["trace"][:3], indent=2))
    print("LEGACY_TRACE_LAST_3")
    print(json.dumps(legacy_trace["trace"][-3:], indent=2))


if __name__ == "__main__":
    main()
