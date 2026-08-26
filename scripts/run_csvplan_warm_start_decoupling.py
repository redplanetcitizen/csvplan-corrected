from __future__ import annotations

"""Test whether the code-only preliminary replacement schedule is a warm start.

This audit starts from the reconciled P3 mechanics but removes two confounders
that let the initial 70% schedule control termination:

1. destinations are tried in ascending Harmony order until one admits a
   strictly positive transfer (ranked fallback);
2. the CV stopping rule is not allowed to accept the untouched warm-start
   state.  At least one search pass must be executed first.  If no positive
   transfer exists on that pass, termination is ``no_transfer_full_pass``.

Preliminary investment is propagated with the exact stock recurrence.  The
level is swept but remains an explicit, non-authorial warm-start parameter.
"""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


RES = Path(__file__).with_name("run_csvplan_residual_code_only_audit.py")
spec = importlib.util.spec_from_file_location("csvplan_residual_for_warm", RES)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load residual audit helpers")
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)

OUT = Path("comparison/warm_start_decoupling")
OUT.mkdir(parents=True, exist_ok=True)


def run_decoupled(v: r.ResidualVariant):
    s, pub = r.build_initial(v)
    initial = r.metrics(s, pub)
    initial_preliminary = float(np.sum(s.investments))
    trace = []
    counter = 1
    accepted = 0
    attempts = 0
    stop = None
    searched_once = False

    while True:
        # A code-only warm start cannot, by itself, satisfy convergence.
        if searched_once:
            cv = float(s.stdh / abs(s.meanh))
            if cv < v.mincoeff:
                stop = "cv"
                break
            if counter > v.maxiter:
                stop = "maxiter"
                break

        destinations = [int(i) for i in np.argsort(s.h)]
        moved = False
        blocked = []
        searched_once = True

        for dest in destinations:
            if dest == 0:
                blocked.append({"destination_year": 0, "reason": "no_previous_source"})
                continue

            attempts += 1
            counter += 1
            before = float(s.meanh)
            cand, source, gain, scale, candidates = r._attempt(s, dest)
            if source is None:
                blocked.append({
                    "destination_year": dest,
                    "reason": "no_positive_source",
                    "scale": float(scale),
                    "candidates": candidates,
                })
                continue

            s = cand
            accepted += 1
            moved = True
            trace.append({
                "counter": counter,
                "destination_year": dest,
                "source_year": int(source),
                "accepted": True,
                "mean_before": before,
                "mean_after": float(s.meanh),
                "best_gain": float(gain),
                "scale": float(scale),
                "blocked_before_move": blocked,
            })
            break

        if not moved:
            stop = "no_transfer_full_pass"
            trace.append({
                "counter": counter,
                "destination_year": None,
                "source_year": None,
                "accepted": False,
                "mean_before": float(s.meanh),
                "mean_after": float(s.meanh),
                "blocked": blocked,
            })
            break

    final = r.metrics(s, pub)
    final.update({
        "accepted_moves": accepted,
        "attempted_corrections": attempts,
        "iterations_counter": counter,
        "stop_reason": stop,
        "initial_preliminary_investment_total": initial_preliminary,
        "published_horizon": pub,
        "computational_horizon": s.prob.TheLastYear,
    })
    return {"variant": r.asdict(v), "initial": initial, "final": final, "trace": trace}


def compact(result):
    f = result["final"]
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
    levels = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
    results = {}
    for level in levels:
        v = r.ResidualVariant(
            name=f"warm_{level:.2f}",
            preliminary_level=level,
            preliminary_scope="all",
            preliminary_timing="exact",
            stop_mode="ranked_fallback",
            mincoeff=legacy.MINCOEFF,
            maxiter=legacy.MAXITER,
        )
        results[v.name] = run_decoupled(v)

    rows = [{"level": level, **compact(results[f"warm_{level:.2f}"])} for level in levels]

    # Pairwise spread after decoupling.  If warm-start levels still produce
    # materially different final states, the initializer is not innocuous and
    # must remain a sensitivity parameter rather than a canonical constant.
    means = np.asarray([x["mean_harmony"] for x in rows])
    cvs = np.asarray([x["cv"] for x in rows])
    mins = np.asarray([x["min_harmony"] for x in rows])
    published_means = np.asarray([x["published_mean_harmony"] for x in rows])

    summary = {
        "rule": "exact preliminary timing + ranked fallback + no CV acceptance before first search pass",
        "levels": rows,
        "spread": {
            "mean_harmony_range": float(np.max(means) - np.min(means)),
            "cv_range": float(np.max(cvs) - np.min(cvs)),
            "min_harmony_range": float(np.max(mins) - np.min(mins)),
            "published_mean_range": float(np.max(published_means) - np.min(published_means)),
        },
        "best_mean": max(rows, key=lambda x: x["mean_harmony"]),
        "best_min": max(rows, key=lambda x: x["min_harmony"]),
        "best_cv": min(rows, key=lambda x: x["cv"]),
    }

    (OUT / "warm_start_full.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "warm_start_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("CSVPLAN_WARM_START_DECOUPLING_SUMMARY")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
