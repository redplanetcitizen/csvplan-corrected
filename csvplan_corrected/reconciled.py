"""Reference reconciled multi-good New Harmony controller.

This module is the implementation target fixed by the completed source/code
adjudication.  It is intentionally distinct from both:

* :mod:`csvplan_corrected.legacy`, the numerical replay of Cockshott's
  historical ``csvplan.jl`` prototype; and
* :mod:`csvplan_corrected.faithful`, the earlier provisional controller built
  before the reconciliation audit was complete.

The controller corrects the confirmed matrix defects and follows the explicit
New Harmony text where the prototype conflicts with it.  Choices that are only
witnessed in executable code, or are our own completion policies, are emitted
as machine-visible provenance rather than silently attributed to Cockshott.

The default *reference demonstration* deliberately retains the historical 70%
preliminary replacement schedule, matrix epsilon, repeat-last shadow policy,
C26 stock-proportional capital update, and first-blocked stopping rule.  Their
presence is for reproducibility and to avoid introducing a new initializer or
capital rule; none of those numerical choices is treated as a theoretical
constant.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import copy
import logging
from pathlib import Path
from typing import Literal

import numpy as np

from . import legacy


LOGGER = logging.getLogger(__name__)
TOL = 1.0e-10

WarmStartPolicy = Literal["historical_matrix_warm_start", "explicit"]
ContinuationPolicy = Literal["repeat_last"]
EpsilonPolicy = Literal["historical_matrix", "text_first_suggestion", "explicit"]
CapitalUpdatePolicy = Literal["historical_matrix_specialization"]
BlockedDestinationPolicy = Literal["historical_first_blocked", "ranked_full_pass"]


@dataclass(frozen=True)
class ReconciledConfig:
    """Reference controls with explicit provenance.

    Defaults define the reproducible audited reference demonstration.  They do
    not assert that code-only values are theoretical New Harmony constants.
    """

    depreciation_horizon: int = legacy.DEPRECIATION_HORIZON
    warm_start_policy: WarmStartPolicy = "historical_matrix_warm_start"
    warm_start_level: float = legacy.INITIAL_INVESTMENT_LEVEL
    continuation_policy: ContinuationPolicy = "repeat_last"
    epsilon_policy: EpsilonPolicy = "historical_matrix"
    epsilon: float | None = None
    harmony_cv_threshold: float = legacy.MINCOEFF
    max_iterations: int = legacy.MAXITER
    capital_update_policy: CapitalUpdatePolicy = "historical_matrix_specialization"
    blocked_destination_policy: BlockedDestinationPolicy = "historical_first_blocked"
    tolerance: float = TOL
    verbose: bool = False

    def validate(self) -> None:
        # The packaged legacy reader currently constructs exactly the historical
        # 14-year shadow window.  The value is surfaced here rather than hidden;
        # alternate horizons require a future reader-level implementation.
        if self.depreciation_horizon != legacy.DEPRECIATION_HORIZON:
            raise NotImplementedError(
                "the reference reader currently supports only the audited "
                f"{legacy.DEPRECIATION_HORIZON}-year shadow horizon"
            )
        if self.continuation_policy != "repeat_last":
            raise NotImplementedError("only the audited repeat_last continuation is packaged")
        if self.capital_update_policy != "historical_matrix_specialization":
            raise NotImplementedError(
                "experimental C26 alternatives are audit profiles, not reference defaults"
            )
        if not (0.0 <= float(self.warm_start_level)):
            raise ValueError("warm_start_level must be nonnegative")
        if self.harmony_cv_threshold < 0.0:
            raise ValueError("harmony_cv_threshold must be nonnegative")
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.tolerance <= 0.0:
            raise ValueError("tolerance must be positive")
        eps = self.resolved_epsilon()
        if not 0.0 < eps < 1.0:
            raise ValueError("resolved epsilon must lie strictly between 0 and 1")

    def resolved_epsilon(self) -> float:
        if self.epsilon_policy == "historical_matrix":
            if self.epsilon is not None:
                raise ValueError("epsilon must be omitted for historical_matrix policy")
            return 0.25 / float(self.depreciation_horizon)
        if self.epsilon_policy == "text_first_suggestion":
            if self.epsilon is not None:
                raise ValueError("epsilon must be omitted for text_first_suggestion policy")
            # The verified first suggestion is 1/(1+1/Delta).  For the reference
            # demo's scalar planning-window calibration Delta=1/H, this is 1/(H+1).
            return 1.0 / (1.0 + float(self.depreciation_horizon))
        if self.epsilon_policy == "explicit":
            if self.epsilon is None:
                raise ValueError("explicit epsilon policy requires epsilon")
            return float(self.epsilon)
        raise ValueError(f"unknown epsilon_policy {self.epsilon_policy!r}")

    def provenance(self) -> dict:
        eps = self.resolved_epsilon()
        return {
            "profile": "reference_reconciled",
            "source_code_adjudication": "CSVPLAN_ADJUDICATION_STATUS.md",
            "warm_start_policy": self.warm_start_policy,
            "warm_start_level": float(self.warm_start_level),
            "warm_start_source_status": "code_only_boundary_condition",
            "warm_start_stock_timing": "exact_recurrence",
            "continuation_policy": self.continuation_policy,
            "continuation_source_status": "code_only_boundary_condition",
            "epsilon_policy": self.epsilon_policy,
            "epsilon": float(eps),
            "epsilon_source_status": (
                "historical_matrix_preset"
                if self.epsilon_policy == "historical_matrix"
                else "text_first_suggestion"
                if self.epsilon_policy == "text_first_suggestion"
                else "explicit_user_parameter"
            ),
            "harmony_cv_threshold": float(self.harmony_cv_threshold),
            "harmony_cv_threshold_source_status": "numerical_parameter",
            "max_iterations": int(self.max_iterations),
            "max_iterations_source_status": "computational_safeguard",
            "depreciation_horizon": int(self.depreciation_horizon),
            "depreciation_horizon_source_status": "demonstration_parameter",
            "capital_update_policy": self.capital_update_policy,
            "capital_update_source_status": "historical_matrix_specialization",
            "blocked_destination_policy": self.blocked_destination_policy,
            "blocked_destination_source_status": (
                "historical_matrix_specialization"
                if self.blocked_destination_policy == "historical_first_blocked"
                else "our_choice_completion_rule"
            ),
            "destination_policy": "global_lowest_harmony",
            "destination_source_status": "explicit_text_rule",
            "source_selection_policy": "best_positive_mean_harmony_gain",
            "depreciation_timing": "exact_stock_recurrence",
            "candidate_positivity": "post_candidate_nonnegative_all_products",
            "robust_harmony": "minimum_all_positive_target_products",
        }


def _coefficient_of_variation(s: legacy.Scenario, tolerance: float) -> float:
    if abs(float(s.meanh)) <= tolerance:
        return float("inf")
    return float(s.stdh / abs(s.meanh))


def _exact_survival(amount: np.ndarray, periods: int, dep: np.ndarray) -> np.ndarray:
    if periods < 0:
        raise ValueError("periods must be nonnegative")
    return np.asarray(amount, dtype=np.float64) * np.power(1.0 - dep, periods)


def _propagate_added_investment_exact(
    stock: np.ndarray,
    source_year: int,
    amount: np.ndarray,
    dep: np.ndarray,
) -> None:
    """Add source-year investment to all later stocks using S[t+1]=(1-d)S[t]+I[t]."""

    first_available = source_year + 1
    for year in range(first_available, stock.shape[0]):
        stock[year] += _exact_survival(amount, year - first_available, dep)


def _inverse_for_destination(
    arrival: np.ndarray,
    source_year: int,
    destination_year: int,
    dep: np.ndarray,
) -> np.ndarray:
    if not 0 <= source_year < destination_year:
        raise ValueError("source year must precede destination year")
    periods = destination_year - source_year - 1
    survival = np.power(1.0 - dep, periods)
    if np.any(survival <= 0.0):
        raise ValueError("non-positive capital survival factor")
    return np.asarray(arrival, dtype=np.float64) / survival


def _refresh_outputs(s: legacy.Scenario) -> None:
    """Correct C13: preserve the product vector when subtracting accumulation."""

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
    final_output = [s.targets[i, :] * ratios[i] for i in range(lastyear)]
    s.netoutputs = [
        final_output[i] - investments_by_type[i, :]
        for i in range(lastyear)
    ]


def _refresh_harmony(s: legacy.Scenario, tolerance: float) -> None:
    """Correct C02/C28 and exclude only nonpositive plan targets from the minimum."""

    lastyear = s.prob.TheLastYear
    product_harmony: list[np.ndarray] = []
    annual = np.zeros(lastyear, dtype=np.float64)

    for year in range(lastyear):
        target = np.asarray(s.prob.g[year, :-1], dtype=np.float64)
        net = np.asarray(s.netoutputs[year], dtype=np.float64)
        active = target > tolerance
        if not np.any(active):
            raise ValueError(f"year {year + 1} has no positive final-product target")
        row = np.full(target.shape, np.nan, dtype=np.float64)
        row[active] = legacy.harmony(net[active] / target[active])
        product_harmony.append(row)
        annual[year] = float(np.min(row[active]))

    # Keep this useful corrected diagnostic even though legacy.Scenario does
    # not declare it in its constructor.
    s.harmony_by_product = product_harmony
    s.h = annual
    s.meanh = float(np.mean(annual))
    s.stdh = float(np.std(annual, ddof=1)) if lastyear > 1 else 0.0


def _refresh(s: legacy.Scenario, tolerance: float) -> None:
    _refresh_outputs(s)
    _refresh_harmony(s, tolerance)


def _build_initial(
    flowname,
    capname,
    depname,
    labtargetsname,
    config: ReconciledConfig,
) -> tuple[legacy.Scenario, int]:
    """Build the reference finite-horizon state with exact warm-start propagation."""

    problem = legacy.readInProblem(flowname, capname, depname, labtargetsname)
    published_horizon = problem.TheLastYear - config.depreciation_horizon
    if published_horizon <= 0:
        raise ValueError("published horizon inferred from the historical reader is nonpositive")

    # Historical matrix Step-1 special handling of the computational final year
    # is retained as an executable implementation specialization.
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
    stock = legacy.Assign_to_each_year_capital_stock(
        problem.caps,
        problem.dep,
        problem.TheLastYear,
    )
    investments = np.zeros(
        (problem.TheLastYear, problem.caprows, problem.capcols),
        dtype=np.float64,
    )

    if config.warm_start_policy == "historical_matrix_warm_start":
        level = float(config.warm_start_level)
    elif config.warm_start_policy == "explicit":
        level = float(config.warm_start_level)
    else:
        raise ValueError(f"unknown warm_start_policy {config.warm_start_policy!r}")

    preliminary = level * (problem.caps * problem.dep)
    for year in range(problem.TheLastYear - 1):
        investments[year] = preliminary
        _propagate_added_investment_exact(stock, year, preliminary, problem.dep)

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
    _refresh(s, config.tolerance)
    return s, published_horizon


def _candidate(
    s: legacy.Scenario,
    source_year: int,
    source_capital: np.ndarray,
    config: ReconciledConfig,
) -> legacy.Scenario:
    s2 = copy.deepcopy(s)
    s2.investments[source_year] += source_capital
    _propagate_added_investment_exact(
        s2.si,
        source_year,
        source_capital,
        s2.prob.dep,
    )
    _refresh(s2, config.tolerance)
    return s2


def _attempt_destination(
    s: legacy.Scenario,
    destination_year: int,
    config: ReconciledConfig,
    epsilon: float,
):
    """Evaluate all preceding source years using the audited C26 specialization."""

    if destination_year <= 0:
        return None, None, 0.0, 0.0, []

    target_ratio = legacy.harmonyInverse(s.meanh)
    current_ratio = legacy.harmonyInverse(s.h[destination_year])
    scale = float((target_ratio - current_ratio) * epsilon)

    # C26 reference decision: retain the only directly witnessed executable
    # multi-good rule, but expose its provenance in the result metadata.
    additional_at_destination = np.maximum(
        s.si[destination_year] * scale,
        0.0,
    )

    best_source = None
    best_gain = 0.0
    best_scenario = None
    candidates: list[dict] = []

    for source_year in range(destination_year):
        source_capital = _inverse_for_destination(
            additional_at_destination,
            source_year,
            destination_year,
            s.prob.dep,
        )
        candidate = _candidate(s, source_year, source_capital, config)
        gain = float(candidate.meanh - s.meanh)
        source_net = np.asarray(candidate.netoutputs[source_year], dtype=np.float64)
        feasible = bool(np.all(source_net >= -config.tolerance))
        candidates.append(
            {
                "source_year": int(source_year),
                "gain": gain,
                "candidate_nonnegative": feasible,
                "candidate_min_net_output_source": float(np.min(source_net)),
                "source_capital_total": float(np.sum(source_capital)),
            }
        )
        if gain > best_gain + config.tolerance and feasible:
            best_source = source_year
            best_gain = gain
            best_scenario = candidate

    return best_scenario, best_source, best_gain, scale, candidates


def _ordered_destinations(s: legacy.Scenario, policy: BlockedDestinationPolicy) -> list[int]:
    order = [int(i) for i in np.argsort(s.h)]
    if policy == "historical_first_blocked":
        return order[:1]
    if policy == "ranked_full_pass":
        return order
    raise ValueError(f"unknown blocked_destination_policy {policy!r}")


def _annual_record(s: legacy.Scenario, year: int) -> dict:
    return {
        "year_index": int(year),
        "harmony": float(s.h[year]),
        "goal_fulfilment_ratio": float(s.goal_fullfilment_ratio_vector[year]),
        "gross_output": np.asarray(s.O[year], dtype=np.float64).copy(),
        "net_output": np.asarray(s.netoutputs[year], dtype=np.float64).copy(),
        "harmony_by_product": np.asarray(s.harmony_by_product[year], dtype=np.float64).copy(),
        "capital_stock_start": np.asarray(s.si[year], dtype=np.float64).copy(),
        "investment": np.asarray(s.investments[year], dtype=np.float64).copy(),
    }


def solve_problem(
    flowname,
    capname,
    depname,
    labtargetsname,
    *,
    config: ReconciledConfig | None = None,
) -> dict:
    """Run the audited reference reconciled controller."""

    config = ReconciledConfig() if config is None else config
    config.validate()
    if config.verbose:
        logging.basicConfig(level=logging.INFO)

    epsilon = config.resolved_epsilon()
    scenario, published_horizon = _build_initial(
        flowname,
        capname,
        depname,
        labtargetsname,
        config,
    )

    initial_harmony = np.asarray(scenario.h, dtype=np.float64).copy()
    trace: list[dict] = []
    accepted = 0
    attempts = 0
    stop_reason = None

    while True:
        cv = _coefficient_of_variation(scenario, config.tolerance)
        if cv < config.harmony_cv_threshold:
            stop_reason = "cv"
            break
        if attempts >= config.max_iterations:
            stop_reason = "maxiter"
            break

        moved = False
        blocked: list[dict] = []
        destinations = _ordered_destinations(scenario, config.blocked_destination_policy)

        for destination_year in destinations:
            if attempts >= config.max_iterations:
                stop_reason = "maxiter"
                break
            if destination_year == 0:
                blocked.append(
                    {"destination_year": 0, "reason": "no_previous_source"}
                )
                if config.blocked_destination_policy == "historical_first_blocked":
                    stop_reason = "no_transfer"
                    break
                continue

            attempts += 1
            mean_before = float(scenario.meanh)
            candidate, source_year, gain, scale, candidates = _attempt_destination(
                scenario,
                destination_year,
                config,
                epsilon,
            )
            if candidate is None or source_year is None:
                blocked.append(
                    {
                        "destination_year": int(destination_year),
                        "reason": "no_positive_source",
                        "scale": float(scale),
                        "candidates": candidates,
                    }
                )
                if config.blocked_destination_policy == "historical_first_blocked":
                    stop_reason = "no_transfer"
                    trace.append(
                        {
                            "attempt": attempts,
                            "destination_year": int(destination_year),
                            "source_year": None,
                            "accepted": False,
                            "mean_before": mean_before,
                            "mean_after": mean_before,
                            "scale": float(scale),
                            "blocked": blocked,
                        }
                    )
                    break
                continue

            if candidate.meanh <= scenario.meanh + config.tolerance:
                raise RuntimeError("candidate selection returned a non-improving move")

            scenario = candidate
            accepted += 1
            moved = True
            trace.append(
                {
                    "attempt": attempts,
                    "destination_year": int(destination_year),
                    "source_year": int(source_year),
                    "accepted": True,
                    "mean_before": mean_before,
                    "mean_after": float(scenario.meanh),
                    "best_gain": float(gain),
                    "scale": float(scale),
                    "blocked_before_move": blocked,
                }
            )
            LOGGER.info(
                "attempt=%d source=%d destination=%d mean_harmony=%.12g",
                attempts,
                source_year + 1,
                destination_year + 1,
                scenario.meanh,
            )
            break

        if stop_reason is not None:
            break
        if not moved:
            stop_reason = "no_transfer_full_pass"
            trace.append(
                {
                    "attempt": attempts,
                    "destination_year": None,
                    "source_year": None,
                    "accepted": False,
                    "mean_before": float(scenario.meanh),
                    "mean_after": float(scenario.meanh),
                    "blocked": blocked,
                }
            )
            break

    computational_annual = [
        _annual_record(scenario, year)
        for year in range(scenario.prob.TheLastYear)
    ]
    net = np.vstack(scenario.netoutputs)
    final_cv = _coefficient_of_variation(scenario, config.tolerance)

    return {
        "scenario": scenario,
        "annual": computational_annual[:published_horizon],
        "shadow_annual": computational_annual[published_horizon:],
        "computational_annual": computational_annual,
        "published_horizon": int(published_horizon),
        "computational_horizon": int(scenario.prob.TheLastYear),
        "provenance": config.provenance(),
        "config": asdict(config),
        "initial_harmony": initial_harmony,
        "harmony": np.asarray(scenario.h, dtype=np.float64).copy(),
        "mean_harmony": float(scenario.meanh),
        "sum_harmony": float(np.sum(scenario.h)),
        "std_harmony": float(scenario.stdh),
        "coefficient_of_variation": float(final_cv),
        "min_harmony": float(np.min(scenario.h)),
        "accepted_moves": int(accepted),
        "attempts": int(attempts),
        "stop_reason": stop_reason,
        "negative_net_output_cells": int(np.sum(net < -config.tolerance)),
        "min_net_output": float(np.min(net)),
        "trace": trace,
    }


def default_data_paths() -> tuple[Path, Path, Path, Path]:
    return legacy.default_data_paths()


def run_default(*, config: ReconciledConfig | None = None) -> dict:
    return solve_problem(*default_data_paths(), config=config)


__all__ = [
    "ReconciledConfig",
    "default_data_paths",
    "run_default",
    "solve_problem",
]
