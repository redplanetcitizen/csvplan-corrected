# csvplan faithful specification

> **AUDIT HOLD. This file is provisional and not normative.** The source/code reconciliation in `CSVPLAN_RECONCILIATION_MATRIX.md` supersedes the implementation decisions below until the csvplan ambiguities have been adjudicated. In particular, the absence of a rule from the prose is not by itself evidence that the corresponding `csvplan.jl` behaviour is erroneous. `faithful.py` must be treated as an experimental reconstruction under audit, not as an established "more faithful" implementation.

## Status and scope

This document records the earlier proposed source hierarchy and implementation requirements for a possible revision of `csvplan-corrected`. It is retained for provenance while the audit is in progress.

The intended target was **a reconstruction of Cockshott's New Harmony multi-year planner**, not a byte-for-byte reproduction of every behaviour of the historical Julia prototype. The historical prototype remains separately replayable through the legacy path.

The normative status of all choices below is suspended until the reconciliation matrix assigns them a final adjudication.

## Source hierarchy (provisional, suspended)

The earlier reconstruction used four witnesses with different roles:

1. **Chapter 6, Theory of Optimal Planning**: consolidated theoretical statement, especially the multi-good extension, finite-horizon discussion, robust annual Harmony, and the nine-step investment algorithm.
2. **Design for Julia implementation of the New Harmony algorithm**: detailed algorithmic specification, tensor stock dynamics, source-to-destination depreciation, positivity condition, and Harmony definitions.
3. **Using csvplan.jl**: previously referenced operational documentation. A standalone primary copy is not currently present in the searchable audit bundle, so remembered contents are not to be used as evidence until the source is recovered.
4. **`csvplan.jl` source**: executable witness.

The earlier precedence rules are suspended. The reconciliation audit now classifies each decision separately as concordance, implementation specialisation, textual variant, code-only, text-only, direct conflict, probable implementation defect, indeterminate, or our choice.

## Earlier proposed mathematical core

### Harmony

Use

`h(x) = x / (1.1 + x)`

on the economically relevant domain.

For each year, compute per-product fulfilment ratios from **net/final social output** and the corresponding target. Annual Harmony was proposed as the minimum per-product Harmony over all products with positive targets:

`H_t = min_i h(f_t,i / g_t,i)`.

The reconciliation audit now treats the historical `[1:end-1]` behaviour separately under C02/C28 rather than silently correcting it.

### Within-period Leontief calculation

For final demand `f_t`, gross output is

`o_t = (I - A)^-1 f_t`.

Investment produced in year `t` is part of final demand in year `t` and becomes productive capital from the start of year `t+1`.

### Capital representation

Use the source-product × user-sector capital requirement matrix `C`, and a time-indexed capital-stock tensor `S[t,i,j]`.

Stock dynamics are

`S[t+1,i,j] = (1 - d[i,j]) * S[t,i,j] + I[t,i,j]`.

Capital feasibility is cell-specific; labour may impose a tighter bound.

## Earlier proposed planning horizon

The user supplies an explicit planning horizon of `T` years through the labour/targets file. The earlier reconstruction proposed automatic extension by `depreciation_horizon` stationary continuation years:

`T_compute = T + depreciation_horizon`.

Historical `csvplan.jl` uses `depreciation_horizon = 14`, repeats the final target/labour data in its extension, and reports only the original input horizon. Chapter 6 independently gives the example of optimising a five-year plan over a 19-year window with a 14-year industrial-capital horizon. The reconciliation audit separates the well-supported 5+14 finite-horizon principle from the code-only details of how shadow rows are generated.

## Earlier proposed initial and terminal treatment

The prior specification removed the Julia-only preliminary rule `initialinvestmentlevel = 0.7`. **That decision is now withdrawn pending audit.** The 70% schedule is classified C14: code-only, not proven erroneous.

The prior Python terminal formalisation is likewise non-normative pending C19/B6 adjudication.

## Earlier proposed intertemporal controller

The earlier reconstruction used below-average destination years, a fixed `epsilon = 0.25 / depreciation_horizon`, best prior source year by positive overall-Harmony gain, mandatory inverse depreciation, post-transfer positivity, and termination if no feasible positive accumulation exists.

Each of these is now separated in the reconciliation matrix:

- destination rule: C05;
- epsilon: C07;
- source-year search: C09;
- overall-Harmony non-reduction: C10;
- inverse depreciation: C11;
- positivity: C12;
- no-transfer termination: C23/C24.

No combined controller is to be declared canonical until the one-factor-at-a-time tests are complete.

## Legacy versus reconstruction

The repository preserves three analytically distinct objects:

- **Cockshott `csvplan.jl` original**: immutable historical prototype sample;
- **Python `legacy.py`**: verified numerical replay of the historical implementation;
- **Python `faithful.py`**: experimental reconstruction currently under audit.

The verified relation is:

`Cockshott csvplan.jl ≈ Python legacy.py`

The reconstruction's divergence is an object of study, not evidence of greater fidelity.

## Audit checkpoint

All further csvplan work is governed by `CSVPLAN_RECONCILIATION_MATRIX.md`.

The next task is to execute Stage A one-factor-at-a-time tests beginning with the accounting issue C13 (matrix row-vector investment subtraction versus Julia scalar linear-index broadcast), while holding every other historical behaviour fixed.