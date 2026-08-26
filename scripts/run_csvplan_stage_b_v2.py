from __future__ import annotations

"""Corrected Stage B runner.

The first Stage B harness built a candidate stock state but failed to refresh its
outputs/Harmony before computing gain.  This wrapper replaces only that helper;
all variant definitions and controller loops remain unchanged.
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
        source_capital = additional_capital
        # Historical default: inverse depreciation remains disabled.
        gain, newscenario = legacy.gainfromInvesting(s, source, source_capital)
        gain = float(gain)
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


m.attempt = attempt


if __name__ == "__main__":
    m.main()
