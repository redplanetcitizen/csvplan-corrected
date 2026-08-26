# csvplan faithful specification

## Status and scope

This document fixes the source hierarchy and implementation requirements for the next revision of `csvplan-corrected`.

The target is **a faithful implementation of Cockshott's New Harmony multi-year planner**, not a byte-for-byte reproduction of every behaviour of the historical Julia prototype. The historical prototype remains separately replayable through the legacy path.

Frozen pre-revision snapshots were created on 2026-08-25/26 as branch `freeze-pre-faithful-2026-08-25` in:

- `redplanetcitizen/csvplan-corrected`
- `redplanetcitizen/NewHarmony_E_Corrected`
- `redplanetcitizen/NewHarmony_Milestone_F_Corrected`

No changes to Milestone E or F are permitted until the faithful csvplan checkpoint defined below has passed.

## Source hierarchy

The reconstruction uses four witnesses with different roles:

1. **Chapter 6, Theory of Optimal Planning**: consolidated theoretical statement, especially the multi-good extension, finite-horizon discussion, robust annual Harmony, and the nine-step investment algorithm.
2. **Design for Julia implementation of the New Harmony algorithm**: detailed algorithmic specification, tensor stock dynamics, source-to-destination depreciation, positivity condition, and Harmony definitions.
3. **Using csvplan.jl**: operational description of the actual Julia program: below-average-year processing, small-fraction adjustment, best preceding source year, three termination conditions, and automatic horizon extension.
4. **`csvplan.jl` source**: executable witness used to resolve implementation details and to identify divergences/bugs. A behaviour present only in the source is not automatically normative.

Precedence rule:

- If Chapter 6 and Design agree, their requirement is normative.
- If `Using csvplan.jl` explicitly documents an operational variant of the multi-good program, that variant is normative for the faithful multi-good controller unless it contradicts a physical/theoretical constraint stated explicitly in Chapter 6 or Design.
- If the Julia source conflicts with an explicit theoretical requirement, preserve the theoretical requirement and record the source divergence as a legacy behaviour.
- If a point is not determined by the texts, mark it as an implementation choice rather than attributing it to Cockshott.

## Required mathematical core

### Harmony

Use

`h(x) = x / (1.1 + x)`

on the economically relevant domain.

For each year, compute per-product fulfilment ratios from **net/final social output** and the corresponding target. Annual Harmony is the minimum per-product Harmony over all products with positive targets:

`H_t = min_i h(f_t,i / g_t,i)`.

Products with zero target are not included in the ratio/minimum, but their net output must remain nonnegative.

This corrects the Julia indexing error in which the last actual product can be dropped by applying `[1:end-1]` after the labour dimension has already disappeared.

### Within-period Leontief calculation

For final demand `f_t`, gross output is

`o_t = (I - A)^-1 f_t`.

Investment produced in year `t` is part of final demand in year `t` and becomes productive capital from the start of year `t+1`.

The Leontief inverse computes **gross output**, not net output.

### Capital representation

Use the source-product × user-sector capital requirement matrix `C`, and a time-indexed capital-stock tensor `S[t,i,j]`.

Stock dynamics are

`S[t+1,i,j] = (1 - d[i,j]) * S[t,i,j] + I[t,i,j]`.

Capital feasibility is cell-specific. For any proposed gross output vector, the binding capital constraint is the minimum stock/required-capital ratio over the active `C[i,j]` cells; labour may impose a tighter bound.

## Planning horizon

The user supplies an explicit planning horizon of `T` years through the labour/targets file.

The computational horizon must be extended automatically by `depreciation_horizon` stationary continuation years:

`T_compute = T + depreciation_horizon`.

Default:

`depreciation_horizon = 14`.

For each continuation year:

- repeat the last explicit target vector;
- repeat the last explicit labour availability;
- keep the same technology and depreciation assumptions unless a later empirical extension explicitly supplies time-varying data.

Only the original `T` years are published as the requested plan. The continuation years exist to remove the artificial incentive to stop investing near the reported horizon.

This requirement reproduces the operational behaviour documented for `csvplan.jl` and the Chapter 6 recommendation that a good five-year plan with a 14-year industrial-capital horizon may be optimised over 19 years and results after year 5 disregarded.

## Initial and terminal treatment

### Initial capital

Start from the supplied capital-stock matrix. Non-terminal endogenous investment starts at zero.

Do **not** reproduce the Julia-only preliminary rule

`initialinvestmentlevel = 0.7`

unless running the legacy replay. This 70% preliminary replacement schedule is present in the source but is not part of the nine-step algorithm and is not documented in `Using csvplan.jl`.

### Final computational year

Apply the Step-1 requirement at the **final computational year**, not the final published year:

- gross output should use the available workforce as fully as physical capital permits;
- sufficient replacement investment should be included to compensate for depreciation during that year;
- the final target remains a scaled version of the target ray.

The corrected Python terminal equation may be retained as an exact algebraic implementation of this requirement, but it must be labelled a corrective formalisation rather than an exact replay of the Julia formula. Its numerical effect must be tested separately against the Julia legacy path.

## Intertemporal controller

### Destination years

The multi-good program is to process **years whose annual Harmony is below the current mean Harmony**. This follows `Using csvplan.jl` and the actual `csvplan.jl` loop.

Do not use the current Python rule "sort every year by Harmony and select the first year for which an admissible correction exists" as the canonical faithful controller.

The generic nine-step description's "select the year with the lowest harmony" is retained as the scalar/general algorithm statement; the documented multi-good `csvplan.jl` controller is the operational rule implemented here.

### Move toward mean Harmony

For a below-average destination year, invert the Harmony function to obtain the fulfilment corresponding to current mean Harmony. Compute the gap from the destination's current fulfilment, then attempt only a small fraction of that gap.

The faithful multi-good default uses the fixed Julia operational value

`epsilon = 0.25 / depreciation_horizon`.

With the default horizon 14:

`epsilon = 1/56 ≈ 0.017857142857`.

Remove adaptive step growth/shrinkage/backtracking from the canonical faithful mode.

Chapter 6 also proposes, "as a first suggestion", the scalar rule `epsilon = 1/(1 + 1/Delta)`. With a matrix of cell-specific depreciation rates there is no uniquely specified scalar `Delta`; therefore this formula is retained as a documented theoretical alternative, not silently substituted for the operational multi-good default.

### Required destination capital

Calculate the additional capital needed to support the attempted destination fulfilment from the target gross output and `C`. Negative gaps are clipped to zero.

### Candidate source years

Consider all years strictly preceding the destination year.

For each source year:

1. undo the relevant source-to-destination depreciation so that the investment produced at the source yields the required surviving capital at the destination;
2. add the proposed investment in the source year;
3. propagate the capital-stock path forward;
4. recompute gross outputs, net outputs, per-product Harmony, annual Harmony and total/mean Harmony;
5. reject any candidate violating flow balance, labour, capital, or nonnegative net-output constraints.

Choose the preceding source year that produces the greatest positive improvement in overall Harmony.

Unlike the historical Julia default (`inversedepreciateinvestments = false`), source-to-destination depreciation compensation is mandatory because Chapter 6 and Design explicitly require it.

### Positivity

The nonnegative-net-output test must be performed on the **candidate scenario after the proposed transfer**, not on the unmodified source scenario. The Julia pre-candidate `posflags` test is treated as a bug.

### Acceptance

Accept a capital transfer only if total/mean Harmony across the computational horizon strictly increases within numerical tolerance.

If no preceding source year yields a feasible positive-Harmony improvement for the current correction attempt, terminate with the documented no-feasible-accumulation condition rather than switching to an adaptive-step search.

## Termination conditions

The faithful controller must terminate under each of the three conditions documented in `Using csvplan.jl`:

1. maximum attempt/iteration count reached;
2. coefficient of variation of annual Harmony falls below the configured threshold;
3. no feasible accumulation can be found that raises overall Harmony.

Default Julia values retained unless tests justify a separately labelled parameterisation:

- `max_iterations = 3000`
- `harmony_cv_threshold = 0.034`

The reason for condition 3 must be reportable; for example, the destination may be labour-bound rather than capital-bound.

## Input contract

The canonical solver continues to require four input tables:

1. input-output flow table;
2. initial capital-stock table;
3. cell-specific depreciation-rate table;
4. labour-supply and final-target table.

`A`, `C`, Leontief inverse, stock trajectories, investments, fulfilments and Harmonies are derived internally.

## Legacy versus faithful behaviour

The repository must preserve three analytically distinct objects:

- **Julia original**: Cockshott's historical `csvplan.jl` source;
- **Python legacy replay**: reproduction of the historical implementation, including source-specific quirks where needed for comparison;
- **Python faithful corrected**: source-based New Harmony implementation with documented prototype bugs corrected.

Expected validation relation:

`Julia original ≈ Python legacy replay`

followed by a controlled comparison

`Python legacy replay != Python faithful corrected`

where every material divergence must map to an explicit item in this specification.

## Required tests before Milestone E may be changed

The faithful csvplan checkpoint requires dedicated tests for:

1. automatic `T + depreciation_horizon` extension;
2. stationary continuation of targets and labour;
3. annual Harmony as the minimum over **all** positive-target products;
4. below-average destination-year processing;
5. fixed `epsilon = 0.25 / depreciation_horizon` in faithful mode;
6. selection of the preceding source year with greatest positive total-Harmony gain;
7. mandatory inverse depreciation from source to destination;
8. post-transfer nonnegative net output;
9. rejection of flow/labour/capital infeasibility;
10. coefficient-of-variation termination;
11. maximum-iteration termination;
12. no-feasible-accumulation termination;
13. final computational-year full-employment/replacement treatment;
14. no preliminary 70% replacement floor in faithful corrected mode;
15. iteration-level comparison against Julia/legacy on the demonstration data.

Only after these tests pass and the Julia/legacy comparison is documented may the controller be ported into Milestone E Corrected.

## Open specification points

The following are not uniquely determined by the sources and must remain explicitly labelled implementation choices:

- how to map the scalar Chapter 6 `Delta` in the suggested epsilon formula to a heterogeneous depreciation matrix `d[i,j]`;
- whether several source years may jointly finance one destination correction in a single iteration (the documented Julia program chooses one best preceding year per attempt);
- exact numerical tolerance conventions;
- the exact matrix formula used to implement Step 1 in the final computational year, provided the full-employment/replacement requirement is satisfied and the choice is documented.
