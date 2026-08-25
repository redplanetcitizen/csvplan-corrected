"""Standalone corrected implementation of Cockshott's csvplan experiment."""

from .solver import (
    ConstraintViolation,
    PlanProblem,
    Scenario,
    SolverConfig,
    TerminalCapitalConstraint,
    YearConstraintReport,
    default_data_paths,
    harmony,
    harmony_inverse,
    read_problem,
    run_default,
    run_default_with_legacy_comparison,
    solve_problem,
    validate_scenario,
)

__version__ = "1.0.0"

__all__ = [
    "ConstraintViolation",
    "PlanProblem",
    "Scenario",
    "SolverConfig",
    "TerminalCapitalConstraint",
    "YearConstraintReport",
    "default_data_paths",
    "harmony",
    "harmony_inverse",
    "read_problem",
    "run_default",
    "run_default_with_legacy_comparison",
    "solve_problem",
    "validate_scenario",
]
