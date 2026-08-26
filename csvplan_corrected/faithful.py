"""Source-faithful multi-year New Harmony controller.

This module implements the controller fixed in ``CSVPLAN_FAITHFUL_SPEC.md``.
It deliberately reuses the corrected accounting/constraint engine in
:mod:`csvplan_corrected.solver` while replacing the adaptive controller with
Cockshott's documented ``csvplan.jl`` operating rules:

* automatic stationary continuation by ``depreciation_horizon`` years;
* processing of years whose Harmony is below the current mean;
* fixed epsilon rather than adaptive backtracking;
* selection of the preceding source year with the largest positive total-
  Harmony gain;
* termination on CV threshold, attempt limit, or absence of a feasible
  positive-Harmony accumulation.

The historical Julia quirks remain in :mod:`csvplan_corrected.legacy` and are
not reproduced here when they conflict with the written New Harmony design.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

import numpy as np

from . import solver


LOGGER = logging.getLogger(__name__)


@dataclass
class FaithfulConfig:
    """Controls whose defaults are documented for the multi-good csvplan path."""

    depreciation_horizon: int = 14
    epsilon: float | None = None
    harmony_cv_threshold: float = 0.034
    max_iterations: int = 3000
    tolerance: float = solver.TOL
    strict: bool = False
    terminal_replacement: bool = True
    verbose: bool = False

    def resolved_epsilon(self) -> float:
        if self.depreciation_horizon <= 0:
            raise ValueError("depreciation_horizon must be positive")
        value = 0.25 / self.depreciation_horizon if self.epsilon is None else float(self.epsilon)
        if not 0.0 < value < 1.0:
            raise ValueError("epsilon must lie strictly between 0 and 1")
        return value


def _evaluation_config(config: FaithfulConfig) -> solver.SolverConfig:
    """Build the accounting-engine config; adaptive fields are intentionally unused."""

    return solver.SolverConfig(
        harmony_cv_threshold=config.harmony_cv_threshold,
        max_iterations=config.max_iterations,
        tolerance=config.tolerance,
        strict=config.strict,
        terminal_replacement=config.terminal_replacement,
        verbose=config.verbose,
    )


def extend_stationary_horizon(
    problem: solver.PlanProblem,
    depreciation_horizon: int,
) -> tuple[solver.PlanProblem, int]:
    """Append Cockshott's stationary continuation years.

    Targets and labour repeat their last explicitly supplied values.  The
    returned integer is the published/input horizon; only those years should be
    reported as the requested plan.
    """

    if depreciation_horizon <= 0:
        raise ValueError("depreciation_horizon must be positive")
    published_horizon = int(problem.horizon)
    if published_horizon < 1:
        raise ValueError("planning problem must contain at least one explicit year")

    target_tail = np.repeat(problem.g[-1:, :], depreciation_horizon, axis=0)
    labour_tail = np.repeat(problem.labouravailable[-1:], depreciation_horizon)

    if published_horizon > 1:
        step = float(problem.years[-1] - problem.years[-2])
        if abs(step) <= config_tolerance(problem.years):
            step = 1.0
    else:
        step = 1.0
    shadow_years = problem.years[-1] + step * np.arange(1, depreciation_horizon + 1, dtype=np.float64)

    g = np.vstack([problem.g, target_tail])
    labour = np.concatenate([problem.labouravailable, labour_tail])
    years = np.concatenate([problem.years, shadow_years])
    labtarg = np.column_stack([years, g, labour])

    extended = solver.PlanProblem(
        headers=list(problem.headers),
        flows=problem.flows.copy(),
        caps=problem.caps.copy(),
        dep=problem.dep.copy(),
        labtarg=labtarg,
        A=problem.A.copy(),
        C=problem.C.copy(),
        D=problem.D.copy(),
        leontief=problem.leontief.copy(),
        g=g,
        labouravailable=labour,
        years=years,
        horizon=int(g.shape[0]),
        products=problem.products,
    )
    return extended, published_horizon


def config_tolerance(values: np.ndarray) -> float:
    """Tiny scale-aware tolerance used only for synthetic year labels."""

    scale = max(1.0, float(np.max(np.abs(values))))
    return np.finfo(np.float64).eps * scale * 16.0


def _coefficient_of_variation(scenario: solver.Scenario, tolerance: float) -> float:
    if abs(scenario.meanh) <= tolerance:
        return np.inf
    return float(scenario.stdh / abs(scenario.meanh))


def _annual_record(problem: solver.PlanProblem, scenario: solver.Scenario, year: int) -> dict:
    end_stock = (1.0 - problem.dep) * scenario.S[year] + scenario.I[year]
    return {
        "year": float(problem.years[year]),
        "gross_output": scenario.O[year].copy(),
        "net_output": scenario.net_output[year].copy(),
        "harmony_by_product": scenario.harmony_by_product[year].copy(),
        "harmony": float(scenario.h[year]),
        "capital_stock_start": scenario.S[year].copy(),
        "capital_stock_end": end_stock,
        "investments": scenario.I[year].copy(),
        "constraints": scenario.constraint_report[year],
        "harmony_mean_over_horizon": float(scenario.meanh),
    }


def solve_problem(
    flowname,
    capname,
    depname,
    labtargetsname,
    *,
    config: FaithfulConfig | None = None,
) -> dict:
    """Run the faithful multi-good New Harmony controller."""

    config = FaithfulConfig() if config is None else config
    if config.verbose:
        logging.basicConfig(level=logging.INFO)

    raw_problem = solver.read_problem(flowname, capname, depname, labtargetsname)
    problem, published_horizon = extend_stationary_horizon(
        raw_problem,
        config.depreciation_horizon,
    )
    evaluation_config = _evaluation_config(config)
    epsilon = config.resolved_epsilon()

    investments = np.zeros(
        (problem.horizon, problem.products, problem.products),
        dtype=np.float64,
    )
    scenario = solver._evaluate(problem, investments, evaluation_config)

    history = [scenario.objective]
    accepted_steps: list[dict] = []
    attempts = 0
    stop_reason = "max_iterations"
    terminated = False

    while attempts < config.max_iterations and not terminated:
        cv = _coefficient_of_variation(scenario, config.tolerance)
        if cv < config.harmony_cv_threshold:
            stop_reason = "converged"
            break

        saw_eligible_year = False
        accepted_in_sweep = False

        # Julia csvplan scans from year 2 onward because year 1 has no possible
        # preceding source year.  The current mean/Harmony are re-read after
        # every accepted correction, as in the mutable Julia scenario.
        for destination_year in range(1, problem.horizon):
            cv = _coefficient_of_variation(scenario, config.tolerance)
            if cv < config.harmony_cv_threshold:
                stop_reason = "converged"
                terminated = True
                break
            if attempts >= config.max_iterations:
                stop_reason = "max_iterations"
                terminated = True
                break

            if scenario.h[destination_year] >= scenario.meanh - config.tolerance:
                continue

            saw_eligible_year = True
            attempts += 1
            candidate, source_year = solver._candidate_for_destination(
                scenario,
                destination_year,
                epsilon,
                evaluation_config,
            )

            if candidate is None or source_year is None:
                stop_reason = "no_feasible_accumulation"
                terminated = True
                break
            if candidate.objective <= scenario.objective + config.tolerance:
                raise solver.ConstraintViolation(
                    "faithful controller accepted a non-improving accumulation"
                )

            objective_before = float(scenario.objective)
            mean_before = float(scenario.meanh)
            scenario = candidate
            history.append(float(scenario.objective))
            accepted_in_sweep = True
            accepted_steps.append(
                {
                    "attempt": attempts,
                    "source_year": int(source_year),
                    "destination_year": int(destination_year),
                    "epsilon": float(epsilon),
                    "objective_before": objective_before,
                    "objective_after": float(scenario.objective),
                    "mean_harmony_before": mean_before,
                    "mean_harmony_after": float(scenario.meanh),
                }
            )
            LOGGER.info(
                "attempt %s: source=%s destination=%s objective=%.12g epsilon=%.9g",
                attempts,
                source_year + 1,
                destination_year + 1,
                scenario.objective,
                epsilon,
            )

        if terminated:
            break
        if not saw_eligible_year or not accepted_in_sweep:
            stop_reason = "no_feasible_accumulation"
            break
    else:
        stop_reason = "max_iterations"

    computational_annual = [
        _annual_record(problem, scenario, year) for year in range(problem.horizon)
    ]
    annual = computational_annual[:published_horizon]
    shadow_annual = computational_annual[published_horizon:]

    if scenario.terminal_capital_limited:
        LOGGER.warning(
            "terminal computational year capital prevents full employment in the accepted scenario"
        )

    return {
        "problem": problem,
        "scenario": scenario,
        "annual": annual,
        "shadow_annual": shadow_annual,
        "computational_annual": computational_annual,
        "published_horizon": published_horizon,
        "computational_horizon": problem.horizon,
        "depreciation_horizon": config.depreciation_horizon,
        "epsilon": epsilon,
        "iterations": len(accepted_steps),
        "attempts": attempts,
        "stop_reason": stop_reason,
        "objective_history": np.asarray(history, dtype=np.float64),
        "accepted_steps": accepted_steps,
        "coefficient_of_variation": _coefficient_of_variation(
            scenario,
            config.tolerance,
        ),
    }


def default_data_paths() -> tuple[Path, Path, Path, Path]:
    return solver.default_data_paths()


def run_default(*, config: FaithfulConfig | None = None) -> dict:
    return solve_problem(*default_data_paths(), config=config)


def compare_with_legacy(faithful_result: dict, legacy_result: dict) -> dict:
    """Compare the faithful corrected path with the autonomous Julia replay."""

    faithful = faithful_result["scenario"]
    legacy = legacy_result["scenario"]
    years = min(faithful.prob.horizon, legacy.prob.TheLastYear)
    legacy_net = np.vstack(legacy.netoutputs[:years])
    faithful_net = faithful.net_output[:years]
    return {
        "years_compared": years,
        "published_horizon": faithful_result["published_horizon"],
        "computational_horizon": faithful_result["computational_horizon"],
        "faithful_mean_harmony": float(faithful.meanh),
        "legacy_mean_harmony": float(np.mean(legacy.h[:years])),
        "faithful_iterations": faithful_result["iterations"],
        "legacy_iterations": legacy_result["iterations"],
        "max_abs_net_output_difference": float(
            np.max(np.abs(faithful_net - legacy_net))
        ),
    }


def run_default_with_legacy_comparison(
    *,
    config: FaithfulConfig | None = None,
) -> dict:
    from . import legacy

    faithful_result = run_default(config=config)
    legacy_result = legacy.run_default(False)
    comparison = compare_with_legacy(faithful_result, legacy_result)
    return {
        "faithful": faithful_result,
        "legacy": legacy_result,
        "comparison": comparison,
    }


__all__ = [
    "FaithfulConfig",
    "compare_with_legacy",
    "default_data_paths",
    "extend_stationary_horizon",
    "run_default",
    "run_default_with_legacy_comparison",
    "solve_problem",
]
