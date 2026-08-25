"""Corrected matrix implementation of Cockshott's New Harmony design.

This module deliberately does *not* reproduce the numerical output of
``csvplan.jl``.  It retains the Julia prototype's useful matrix/tensor model
while enforcing the accounting and intertemporal constraints stated in
``Design for Julia implementation of the New Harmony algorithm``.

The companion :mod:`csvplan_corrected.legacy` module is the numerical compatibility
oracle.  Keeping the two implementations separate makes every divergence
auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import copy
import csv
import logging

import numpy as np


LOGGER = logging.getLogger(__name__)
TOL = 1.0e-9


class ConstraintViolation(RuntimeError):
    """Raised when a scenario violates a physical or accounting invariant."""


class TerminalCapitalConstraint(RuntimeError):
    """Raised in strict mode when terminal capital prevents full employment."""


@dataclass
class PlanProblem:
    """Input data and derived matrices for the corrected planning problem."""

    headers: list[str]
    flows: np.ndarray
    caps: np.ndarray
    dep: np.ndarray
    labtarg: np.ndarray
    A: np.ndarray
    C: np.ndarray
    D: np.ndarray
    leontief: np.ndarray
    g: np.ndarray
    labouravailable: np.ndarray
    years: np.ndarray
    horizon: int
    products: int


@dataclass
class YearConstraintReport:
    """Constraint audit for one year of a scenario."""

    year: int
    flow_balance_ok: bool
    labour_ok: bool
    capital_ok: bool
    consumption_ok: bool
    max_flow_residual: float
    labour_used: float
    labour_available: float
    max_capital_excess: float
    min_consumption: float

    @property
    def compliant(self) -> bool:
        return (
            self.flow_balance_ok
            and self.labour_ok
            and self.capital_ok
            and self.consumption_ok
        )


@dataclass
class Scenario:
    """Complete intertemporal state produced by one investment schedule."""

    prob: PlanProblem
    S: np.ndarray
    I: np.ndarray
    O: np.ndarray
    final_available: np.ndarray
    net_output: np.ndarray
    lambdas: np.ndarray
    harmony_by_product: np.ndarray
    h: np.ndarray
    meanh: float
    stdh: float
    objective: float
    constraint_report: list[YearConstraintReport] = field(default_factory=list)
    terminal_capital_limited: bool = False


@dataclass
class SolverConfig:
    """Numerical and convergence controls for the corrected solver."""

    harmony_cv_threshold: float = 0.034
    max_iterations: int = 3000
    initial_step: float = 0.25
    minimum_step: float = 1.0e-5
    maximum_step: float = 0.5
    step_growth: float = 1.15
    step_shrink: float = 0.5
    tolerance: float = TOL
    strict: bool = False
    terminal_replacement: bool = True
    verbose: bool = False


def _read_csv_numeric(path: str | Path) -> tuple[np.ndarray, list[str]]:
    path = Path(path)
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [[float(cell) for cell in row] for row in reader if row]
    return np.asarray(rows, dtype=np.float64), headers


def _normalise_flow_matrix(flowmatrix: np.ndarray) -> np.ndarray:
    """Return augmented A; Design section 5, equations (12)-(14)."""

    rows, cols = flowmatrix.shape
    if rows != cols + 2:
        raise ValueError("flow table must contain products, labour, and gross output")
    gross = flowmatrix[-1, :]
    if np.any(gross <= 0.0):
        raise ValueError("gross output entries must be positive")
    rectangular = flowmatrix[:-1, :] / gross[None, :]
    return np.hstack([rectangular, np.zeros((rows - 1, 1), dtype=np.float64)])


def _normalise_capital_matrix(flowmatrix: np.ndarray, caps: np.ndarray) -> np.ndarray:
    """Return augmented C; Design section 5, capital-constraint discussion."""

    products = flowmatrix.shape[1]
    if caps.shape != (products, products):
        raise ValueError("capital table must be products x products")
    gross = flowmatrix[-1, :]
    full = np.zeros((products + 1, products + 1), dtype=np.float64)
    full[:products, :products] = caps / gross[None, :]
    return full


def read_problem(flowname, capname, depname, labtargetsname) -> PlanProblem:
    """Read the four csvplan inputs without adding the Julia terminal buffer."""

    flows, flow_headers = _read_csv_numeric(flowname)
    caps, cap_headers = _read_csv_numeric(capname)
    dep, dep_headers = _read_csv_numeric(depname)
    labtarg, headers = _read_csv_numeric(labtargetsname)
    products = flows.shape[1]
    expected = flow_headers
    if cap_headers != expected or dep_headers != expected:
        raise ValueError("flow, capital, and depreciation column order must match")
    if headers[0] != "Year" or headers[-1] != "Labour":
        raise ValueError("target table must start with Year and end with Labour")
    if headers[1:-1] != expected:
        raise ValueError("target product order must match the input-output table")
    if dep.shape != caps.shape or np.any(dep < 0.0) or np.any(dep >= 1.0):
        raise ValueError("depreciation rates must have capital-table shape and lie in [0,1)")

    A = _normalise_flow_matrix(flows)
    C = _normalise_capital_matrix(flows, caps)
    D = np.zeros_like(C)
    D[:products, :products] = C[:products, :products] * dep
    identity = np.eye(A.shape[0])
    leontief = np.linalg.inv(identity - A)
    g = labtarg[:, 1:-1].astype(np.float64, copy=True)
    labour = labtarg[:, -1].astype(np.float64, copy=True)
    years = labtarg[:, 0].astype(np.float64, copy=True)
    return PlanProblem(
        headers=headers,
        flows=flows,
        caps=caps,
        dep=dep,
        labtarg=labtarg,
        A=A,
        C=C,
        D=D,
        leontief=leontief,
        g=g,
        labouravailable=labour,
        years=years,
        horizon=g.shape[0],
        products=products,
    )


def harmony(x):
    """Harmony H(x)=x/(1.1+x); Design equation (6)."""

    values = np.asarray(x, dtype=np.float64)
    return values / (1.1 + values)


def harmony_inverse(h):
    """Analytical inverse of Design equation (6)."""

    values = np.asarray(h, dtype=np.float64)
    return 1.1 * values / (1.0 - values)


def propagate_stock(initial: np.ndarray, investments: np.ndarray, dep: np.ndarray) -> np.ndarray:
    """Apply S[t+1]=(1-D)*S[t]+I[t]; Design equation (3)."""

    horizon = investments.shape[0]
    stocks = np.zeros_like(investments, dtype=np.float64)
    stocks[0] = np.asarray(initial, dtype=np.float64)
    for year in range(horizon - 1):
        stocks[year + 1] = (1.0 - dep) * stocks[year] + investments[year]
    return stocks


def inverse_depreciate(
    required_at_destination: np.ndarray,
    source_year: int,
    destination_year: int,
    dep: np.ndarray,
) -> np.ndarray:
    """Undo exponential depreciation; Design, comment on step 8, p. 6."""

    if not 0 <= source_year < destination_year:
        raise ValueError("source year must precede destination year")
    exponent = destination_year - source_year - 1
    return np.asarray(required_at_destination, dtype=np.float64) / np.power(1.0 - dep, exponent)


def investment_vector(investment_matrix: np.ndarray) -> np.ndarray:
    """Aggregate capital allocations by producing good, preserving product identity."""

    return np.sum(investment_matrix, axis=1)


def _augmented(vector: np.ndarray) -> np.ndarray:
    return np.concatenate([np.asarray(vector, dtype=np.float64), np.zeros(1)])


def _capital_requirement(problem: PlanProblem, gross: np.ndarray) -> np.ndarray:
    """Compute c[i,j]*o[j]; Design section 5, p. 12."""

    n = problem.products
    return problem.C[:n, :n] * gross[:n][None, :]


def max_consumption_scale(
    problem: PlanProblem,
    stock: np.ndarray,
    investment: np.ndarray,
    year: int,
    *,
    tolerance: float = TOL,
) -> tuple[float, np.ndarray]:
    """Solve x(lambda)=(I-A)^-1(lambda*g+i); corrected requirement 8."""

    goal = _augmented(problem.g[year])
    inv = _augmented(investment_vector(investment))
    gross_goal = problem.leontief @ goal
    gross_investment = problem.leontief @ inv
    labour_coeff = problem.A[-1, :]

    bounds: list[float] = []
    labour_base = float(labour_coeff @ gross_investment)
    labour_slope = float(labour_coeff @ gross_goal)
    if labour_base > problem.labouravailable[year] + tolerance:
        return -1.0, gross_investment
    if labour_slope > tolerance:
        bounds.append((problem.labouravailable[year] - labour_base) / labour_slope)

    capital_coeff = problem.C[: problem.products, : problem.products]
    for row in range(problem.products):
        for col in range(problem.products):
            coeff = capital_coeff[row, col]
            if coeff <= tolerance:
                continue
            base = coeff * gross_investment[col]
            slope = coeff * gross_goal[col]
            available = stock[row, col]
            if base > available + tolerance:
                return -1.0, gross_investment
            if slope > tolerance:
                bounds.append((available - base) / slope)

    if not bounds:
        raise ConstraintViolation("consumption scale is unbounded: no labour or capital constraint")
    lam = max(0.0, float(min(bounds)))
    gross = gross_investment + lam * gross_goal
    return lam, gross


def terminal_replacement(
    problem: PlanProblem,
    stock: np.ndarray,
    year: int,
    *,
    strict: bool,
    tolerance: float,
    emit_warning: bool = False,
) -> tuple[np.ndarray, float, bool]:
    """Solve x=(I-A-D)^-1(q*g); corrected terminal requirement 9."""

    augmented_goal = _augmented(problem.g[year])
    base_gross = np.linalg.solve(np.eye(problem.A.shape[0]) - problem.A - problem.D, augmented_goal)
    labour_coeff = problem.A[-1, :]
    labour_base = float(labour_coeff @ base_gross)
    q_labour = np.inf if labour_base <= tolerance else problem.labouravailable[year] / labour_base

    capital_bounds: list[float] = []
    required_base = _capital_requirement(problem, base_gross)
    mask = required_base > tolerance
    capital_bounds.extend((stock[mask] / required_base[mask]).tolist())
    q_capital = min(capital_bounds) if capital_bounds else np.inf
    capital_limited = q_capital + tolerance < q_labour
    if capital_limited:
        message = (
            f"terminal year {year + 1}: capital permits q={q_capital:.8g}, "
            f"below full-employment q={q_labour:.8g}"
        )
        if emit_warning:
            LOGGER.warning(message)
        if strict:
            raise TerminalCapitalConstraint(message)
    q = max(0.0, float(min(q_labour, q_capital)))
    gross = q * base_gross
    replacement = problem.D[: problem.products, : problem.products] * gross[: problem.products][None, :]
    return replacement, q, capital_limited


def _year_report(
    problem: PlanProblem,
    scenario: Scenario,
    year: int,
    tolerance: float,
) -> YearConstraintReport:
    gross = scenario.O[year]
    inv = investment_vector(scenario.I[year])
    rhs = _augmented(scenario.net_output[year] + inv)
    residual = (np.eye(problem.A.shape[0]) - problem.A) @ gross - rhs
    max_flow_residual = float(np.max(np.abs(residual)))
    labour_used = float(problem.A[-1, :] @ gross)
    capital_required = _capital_requirement(problem, gross)
    capital_excess = capital_required - scenario.S[year]
    max_capital_excess = float(np.max(capital_excess))
    min_consumption = float(np.min(scenario.net_output[year]))
    scale = max(1.0, float(np.max(np.abs(rhs))))
    return YearConstraintReport(
        year=year,
        flow_balance_ok=max_flow_residual <= tolerance * scale,
        labour_ok=labour_used <= problem.labouravailable[year] + tolerance * max(1.0, problem.labouravailable[year]),
        capital_ok=max_capital_excess <= tolerance * max(1.0, float(np.max(scenario.S[year]))),
        consumption_ok=min_consumption >= -tolerance,
        max_flow_residual=max_flow_residual,
        labour_used=labour_used,
        labour_available=float(problem.labouravailable[year]),
        max_capital_excess=max_capital_excess,
        min_consumption=min_consumption,
    )


def validate_scenario(
    scenario: Scenario,
    *,
    strict: bool = True,
    tolerance: float = TOL,
) -> list[YearConstraintReport]:
    """Audit flow balance, labour, capital, and positivity requirements 1/5/8."""

    reports = [_year_report(scenario.prob, scenario, year, tolerance) for year in range(scenario.prob.horizon)]
    scenario.constraint_report = reports
    failures = [report for report in reports if not report.compliant]
    if failures and strict:
        years = ", ".join(str(report.year + 1) for report in failures)
        raise ConstraintViolation(f"scenario violates constraints in year(s): {years}")
    return reports


def _evaluate(
    problem: PlanProblem,
    investments: np.ndarray,
    config: SolverConfig,
) -> Scenario:
    investments = np.asarray(investments, dtype=np.float64).copy()
    if investments.shape != (problem.horizon, problem.products, problem.products):
        raise ValueError("investment tensor has wrong shape")
    if np.any(investments < -config.tolerance):
        raise ConstraintViolation("investment tensor contains negative entries")
    investments[-1] = 0.0
    stocks = propagate_stock(problem.caps, investments, problem.dep)
    terminal_limited = False
    if config.terminal_replacement:
        replacement, _, terminal_limited = terminal_replacement(
            problem,
            stocks[-1],
            problem.horizon - 1,
            strict=config.strict,
            tolerance=config.tolerance,
            emit_warning=False,
        )
        investments[-1] = replacement

    output = np.zeros((problem.horizon, problem.products + 1), dtype=np.float64)
    final_available = np.zeros((problem.horizon, problem.products), dtype=np.float64)
    consumption = np.zeros_like(final_available)
    lambdas = np.zeros(problem.horizon, dtype=np.float64)
    harmony_products = np.full_like(final_available, np.nan)
    annual_harmony = np.zeros(problem.horizon, dtype=np.float64)

    for year in range(problem.horizon):
        lam, gross = max_consumption_scale(
            problem,
            stocks[year],
            investments[year],
            year,
            tolerance=config.tolerance,
        )
        if lam < -config.tolerance:
            raise ConstraintViolation(f"investment alone is infeasible in year {year + 1}")
        lam = max(0.0, lam)
        output[year] = gross
        total_final = ((np.eye(problem.A.shape[0]) - problem.A) @ gross)[: problem.products]
        inv_vector = investment_vector(investments[year])
        final_available[year] = total_final
        consumption[year] = total_final - inv_vector
        lambdas[year] = lam
        positive_targets = problem.g[year] > config.tolerance
        zero_targets = ~positive_targets
        if np.any(consumption[year, zero_targets] < -config.tolerance):
            raise ConstraintViolation(f"negative output for zero-target product in year {year + 1}")
        if not np.any(positive_targets):
            raise ConstraintViolation(f"year {year + 1} has no positive target")
        ratios = consumption[year, positive_targets] / problem.g[year, positive_targets]
        harmony_products[year, positive_targets] = harmony(ratios)
        annual_harmony[year] = float(np.min(harmony_products[year, positive_targets]))

    scenario = Scenario(
        prob=problem,
        S=stocks,
        I=investments,
        O=output,
        final_available=final_available,
        net_output=consumption,
        lambdas=lambdas,
        harmony_by_product=harmony_products,
        h=annual_harmony,
        meanh=float(np.mean(annual_harmony)),
        stdh=float(np.std(annual_harmony, ddof=1)) if problem.horizon > 1 else 0.0,
        objective=float(np.sum(annual_harmony)),
        terminal_capital_limited=terminal_limited,
    )
    validate_scenario(scenario, strict=config.strict, tolerance=config.tolerance)
    return scenario


def additional_capital_for_scale(
    scenario: Scenario,
    destination_year: int,
    target_lambda: float,
) -> np.ndarray:
    """Use C[i,j]*o[j]-S[i,j]; corrected requirement 7."""

    problem = scenario.prob
    inv = _augmented(investment_vector(scenario.I[destination_year]))
    target_final = target_lambda * _augmented(problem.g[destination_year]) + inv
    target_gross = problem.leontief @ target_final
    required = _capital_requirement(problem, target_gross)
    return np.maximum(required - scenario.S[destination_year], 0.0)


def _candidate_for_destination(
    scenario: Scenario,
    destination_year: int,
    step: float,
    config: SolverConfig,
) -> tuple[Scenario | None, int | None]:
    target_harmony = scenario.meanh
    target_lambda = float(harmony_inverse(target_harmony))
    current_lambda = scenario.lambdas[destination_year]
    if target_lambda <= current_lambda + config.tolerance:
        return None, None
    attempted_lambda = current_lambda + step * (target_lambda - current_lambda)
    needed_at_destination = additional_capital_for_scale(scenario, destination_year, attempted_lambda)
    if float(np.max(needed_at_destination)) <= config.tolerance:
        return None, None

    best: Scenario | None = None
    best_source: int | None = None
    for source_year in range(destination_year):
        source_investment = inverse_depreciate(
            needed_at_destination,
            source_year,
            destination_year,
            scenario.prob.dep,
        )
        proposal = scenario.I.copy()
        proposal[source_year] += source_investment
        try:
            candidate = _evaluate(scenario.prob, proposal, config)
        except (ConstraintViolation, TerminalCapitalConstraint, np.linalg.LinAlgError):
            continue
        if candidate.objective <= scenario.objective + config.tolerance:
            continue
        if best is None or candidate.objective > best.objective:
            best = candidate
            best_source = source_year
    return best, best_source


def solve_problem(
    flowname,
    capname,
    depname,
    labtargetsname,
    *,
    config: SolverConfig | None = None,
) -> dict:
    """Run corrected steps 3-9 with admissible-year selection and adaptive step."""

    config = copy.deepcopy(config) if config is not None else SolverConfig()
    if config.verbose:
        logging.basicConfig(level=logging.INFO)
    problem = read_problem(flowname, capname, depname, labtargetsname)
    investments = np.zeros((problem.horizon, problem.products, problem.products), dtype=np.float64)
    scenario = _evaluate(problem, investments, config)
    history = [scenario.objective]
    accepted_steps: list[dict] = []
    step = config.initial_step
    stop_reason = "max_iterations"

    for iteration in range(1, config.max_iterations + 1):
        cv = np.inf if abs(scenario.meanh) <= config.tolerance else scenario.stdh / abs(scenario.meanh)
        if cv < config.harmony_cv_threshold:
            stop_reason = "converged"
            break

        accepted: Scenario | None = None
        accepted_destination: int | None = None
        accepted_source: int | None = None
        trial_step = step
        while trial_step >= config.minimum_step and accepted is None:
            eligible_years = sorted(range(1, problem.horizon), key=lambda year: scenario.h[year])
            for destination_year in eligible_years:
                candidate, source_year = _candidate_for_destination(
                    scenario,
                    destination_year,
                    trial_step,
                    config,
                )
                if candidate is not None:
                    accepted = candidate
                    accepted_destination = destination_year
                    accepted_source = source_year
                    break
            if accepted is None:
                trial_step *= config.step_shrink

        if accepted is None:
            stop_reason = "no_admissible_correction" if trial_step >= config.minimum_step else "minimum_step"
            break
        if accepted.objective <= scenario.objective + config.tolerance:
            raise ConstraintViolation("accepted scenario does not improve total Harmony")

        old_objective = scenario.objective
        old_mean_harmony = scenario.meanh
        scenario = accepted
        history.append(scenario.objective)
        accepted_steps.append(
            {
                "iteration": iteration,
                "source_year": int(accepted_source),
                "destination_year": int(accepted_destination),
                "step": float(trial_step),
                "objective_before": float(old_objective),
                "objective_after": float(scenario.objective),
            }
        )
        # A switch of the weakest year is normal equalisation, not by itself an
        # oscillation.  Shrink the next step only on an actual overshoot: the
        # corrected destination has crossed above the previous mean Harmony.
        oscillating = scenario.h[accepted_destination] > old_mean_harmony + config.tolerance
        accepted_steps[-1]["oscillation_detected"] = oscillating
        if oscillating:
            step = max(config.minimum_step, trial_step * config.step_shrink)
        else:
            step = min(config.maximum_step, trial_step * config.step_growth)
        LOGGER.info(
            "iteration %s: source=%s destination=%s objective=%.12g step=%.6g",
            iteration,
            accepted_source + 1,
            accepted_destination + 1,
            scenario.objective,
            trial_step,
        )
    else:
        iteration = config.max_iterations

    annual = []
    for year in range(problem.horizon):
        end_stock = (1.0 - problem.dep) * scenario.S[year] + scenario.I[year]
        annual.append(
            {
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
        )
    if scenario.terminal_capital_limited:
        LOGGER.warning(
            "terminal capital prevents full employment in the accepted final scenario"
        )
    return {
        "problem": problem,
        "scenario": scenario,
        "annual": annual,
        "iterations": len(accepted_steps),
        "stop_reason": stop_reason,
        "objective_history": np.asarray(history, dtype=np.float64),
        "accepted_steps": accepted_steps,
        "coefficient_of_variation": (
            np.inf if abs(scenario.meanh) <= config.tolerance else scenario.stdh / abs(scenario.meanh)
        ),
    }


def compare_with_legacy(corrected_result: dict, legacy_result: dict) -> dict:
    """Return a compact, explicit comparison without asserting equal outputs."""

    corrected = corrected_result["scenario"]
    legacy = legacy_result["scenario"]
    years = min(corrected.prob.horizon, legacy.prob.TheLastYear)
    legacy_net = np.vstack(legacy.netoutputs[:years])
    return {
        "years_compared": years,
        "corrected_mean_harmony": corrected.meanh,
        "legacy_mean_harmony": float(np.mean(legacy.h[:years])),
        "corrected_iterations": corrected_result["iterations"],
        "legacy_iterations": legacy_result["iterations"],
        "max_abs_net_output_difference": float(np.max(np.abs(corrected.net_output[:years] - legacy_net))),
        "legacy_negative_outputs_hidden": bool(
            np.any(
                (
                    np.vstack(
                        [
                            legacy.targets[year] * legacy.goal_fullfilment_ratio_vector[year]
                            - legacy.investmentsByTypeAndYear[year]
                            for year in range(years)
                        ]
                    )
                )
                < -TOL
            )
        ),
    }


def run_default_with_legacy_comparison(
    *,
    config: SolverConfig | None = None,
) -> dict:
    """Run both solvers and log the comparison requested by the delivery brief."""

    from . import legacy

    corrected_result = run_default(config=config)
    legacy_result = legacy.run_default(False)
    comparison = compare_with_legacy(corrected_result, legacy_result)
    LOGGER.info(
        "legacy/corrected: mean Harmony %.8f/%.8f; iterations %s/%s; "
        "max net-output difference %.6g; hidden legacy negatives=%s",
        comparison["legacy_mean_harmony"],
        comparison["corrected_mean_harmony"],
        comparison["legacy_iterations"],
        comparison["corrected_iterations"],
        comparison["max_abs_net_output_difference"],
        comparison["legacy_negative_outputs_hidden"],
    )
    return {
        "corrected": corrected_result,
        "legacy": legacy_result,
        "comparison": comparison,
    }


def default_data_paths() -> tuple[Path, Path, Path, Path]:
    data = Path(__file__).resolve().parent / "data"
    return (
        data / "jeuflows.csv",
        data / "jeucap.csv",
        data / "jeudep.csv",
        data / "jeulabtargs.csv",
    )


def run_default(*, config: SolverConfig | None = None) -> dict:
    return solve_problem(*default_data_paths(), config=config)


__all__ = [
    "ConstraintViolation",
    "TerminalCapitalConstraint",
    "PlanProblem",
    "Scenario",
    "SolverConfig",
    "YearConstraintReport",
    "additional_capital_for_scale",
    "compare_with_legacy",
    "default_data_paths",
    "harmony",
    "harmony_inverse",
    "inverse_depreciate",
    "max_consumption_scale",
    "propagate_stock",
    "read_problem",
    "run_default",
    "run_default_with_legacy_comparison",
    "solve_problem",
    "terminal_replacement",
    "validate_scenario",
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_default_with_legacy_comparison(config=SolverConfig(strict=False, verbose=True))
