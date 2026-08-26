from __future__ import annotations

"""Corrected Stage B runner.

This wrapper fixes two audit-harness issues without changing any tested csvplan
variant: candidate scenarios are fully re-evaluated before gain is measured, and
the historical no-transfer stop reason is retained while the current scan
finishes for counter compatibility.
"""

import importlib.util
from pathlib import Path
import sys

import numpy as np

from csvplan_corrected import legacy


BASE = Path(__file__).with_name("run_csvplan_stage_b.py")
spec = importlib.util.spec_from_file_location("csvplan_stage_b_base", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load Stage B base module")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


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
        gain, newscenario = legacy.gainfromInvesting(s, source, additional_capital)
        gain = float(gain)
        posflags = s.netoutputs[source][:n] > np.zeros(n)
        feasible = bool(np.prod(posflags))
        candidate_rows.append({"source_year": source, "gain": gain, "historical_precheck": feasible})
        if gain > best_gain and feasible:
            best_year = source
            best_gain = gain
            best_scenario = newscenario
    return best_scenario, best_year, best_gain, scale_increment, candidate_rows


def run_sequential(v, s):
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
                    trace.append({
                        "counter": iter_count, "destination_year": dest, "source_year": None,
                        "accepted": False, "mean_before": before, "mean_after": before,
                        "best_gain": 0.0, "scale_increment": scale, "candidates": candidates,
                    })
                    if v.no_transfer_mode == "stop_immediately":
                        stop_reason = "no_transfer"
                        doagain = False
                else:
                    s = cand
                    accepted += 1
                    accepted_this_pass += 1
                    trace.append({
                        "counter": iter_count, "destination_year": dest, "source_year": int(source),
                        "accepted": True, "mean_before": before, "mean_after": float(s.meanh),
                        "best_gain": float(gain), "scale_increment": scale,
                    })
        if not doagain:
            break
        if v.no_transfer_mode == "continue_scan" and accepted_this_pass == 0 and failed_this_pass > 0:
            stop_reason = "no_transfer_full_pass"
            doagain = False
        elif v.no_transfer_mode == "continue_scan" and accepted_this_pass == 0:
            stop_reason = "no_below_mean_correction"
            doagain = False
    return s, trace, iter_count, accepted, attempts, stop_reason


m.attempt = attempt
m.run_sequential = run_sequential


if __name__ == "__main__":
    m.main()
