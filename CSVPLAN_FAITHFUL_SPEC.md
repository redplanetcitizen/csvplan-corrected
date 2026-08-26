# csvplan reconstruction specification

> **STATUS: SOURCE/CODE ADJUDICATION COMPLETE FOR THE REFERENCE PROFILE.** C14 and the residual code-only controls have been classified and C26 has been closed as a retention decision. The next task is implementation: replace the older provisional `faithful.py` semantics with a provenance-explicit reference reconciled module and rerun the full numerical gate. This specification does not erase the distinction between the historical prototype, the printed New Harmony procedure, and our completion policies.

## 1. Objects kept distinct

The repository contains three analytically different objects.

1. **Cockshott `csvplan.jl` original**: immutable historical prototype sample.
2. **`legacy.py`**: verified Python numerical replay of the historical prototype.
3. **reference reconciled reconstruction**: corrects confirmed defects, follows explicit textual prescriptions where the prototype conflicts with them, and visibly labels executable choices not uniquely fixed by the text.

The valid historical relation is `csvplan.jl ≈ legacy.py`. A different numerical result from the reconciled reconstruction is not evidence of greater fidelity by itself.

## 2. Evidence and precedence

Primary witnesses used in the adjudication:

- Chapter 6, `Theory of Optimal Planning`;
- `Design for Julia implementation of the New Harmony algorithm`;
- scalar `harmony2.jl` where it illuminates the printed procedure;
- matrix `csvplan.jl` as executable historical witness.

Decision precedence is row-specific:

- a confirmed programming defect is corrected when the surrounding model and text identify the intended object;
- an explicit textual algorithmic prescription prevails over a conflicting active prototype path, while the latter remains historically replayable;
- code-only values remain historical/reproducibility parameters and are not promoted to theoretical constants;
- where the text is indeterminate, the directly witnessed matrix specialization is retained unless a reconstruction is explicitly chosen and labelled.

See `CSVPLAN_RECONCILIATION_MATRIX.md`, `CSVPLAN_ADJUDICATION_STATUS.md`, `CSVPLAN_RESIDUAL_CODE_ONLY_ADJUDICATION.md`, and `CSVPLAN_C26_ADJUDICATION.md`.

## 3. Mathematical core

### 3.1 Fractional Harmony

Use `h(x) = x / (1.1 + x)`.

For each year, compute fulfilment ratios from net/final social output and positive plan targets. Robust annual Harmony is the minimum product Harmony over **all** positive-target final products. Labour is a constraint, not a final product in this minimum.

### 3.2 Within-period Leontief calculation

For final demand `f_t`, gross output is

`o_t = (I - A)^-1 f_t`.

Investment produced in year `t` belongs to final demand in that year and becomes productive capital from `t+1`.

### 3.3 Capital stocks

Use source-product × user-sector capital requirements `C` and stock tensor `S[t,i,j]` with

`S[t+1,i,j] = (1 - d[i,j]) * S[t,i,j] + I[t,i,j]`.

Capital feasibility is cell-specific; labour is an additional aggregate constraint.

### 3.4 Candidate transfers

Investment shifted from a preceding source year to a later destination must be inverse-adjusted so that the amount arriving at the destination equals the required surviving capital under the stock recurrence.

Candidate-state net outputs, not the pre-transfer state, determine non-negativity. An accepted move must strictly increase total/mean Harmony within numerical tolerance.

## 4. Intertemporal destination and source

Design, Chapter 6, and scalar `harmony2.jl` prescribe selecting the year with the **lowest Harmony**. The active sequential-below-mean scan in `csvplan.jl` is historical prototype behavior, not the reference reconciled destination rule.

Reference rule:

1. begin with the globally lowest-Harmony year;
2. consider only source years strictly preceding it;
3. choose the source producing the largest positive total/mean-Harmony gain among feasible candidates.

If the worst year is blocked, the text does not uniquely prescribe a completion rule. Two provenance-labelled options are admissible:

- `historical_first_blocked`: terminate immediately;
- `ranked_full_pass`: try subsequent years in ascending Harmony order and terminate only after a full failed pass. This is **our completion rule**, not an attributed Cockshott step.

The reproducible reference run must state which option is active.

## 5. Finite planning horizon and shadow continuation

The published horizon is `T`; the computational horizon may extend beyond `T` to prevent artificial terminal disinvestment. Chapter 6 explicitly gives the five-year plus fourteen-year example, producing a nineteen-year calculation window.

The economic content of shadow rows is not uniquely fixed by that principle. Therefore output must distinguish:

- `published_horizon`;
- `computational_horizon`;
- `continuation_policy`.

`repeat_last` reproduces the matrix prototype's continuation of the final explicit targets and labour. It is a reproducibility/boundary policy, not a theoretical invariant. The residual audit shows shadow assumptions materially affect published-period results.

## 6. C14: preliminary investment / warm start

### 6.1 Historical fact

Matrix `csvplan.jl` uses `initialinvestmentlevel = 0.7` and preassigns 70% of replacement investment before iterative search.

### 6.2 Source status

The verified nine-step procedure does not state a uniform preliminary percentage. It starts from depreciated initial stocks and then shifts/schedules investment endogenously.

### 6.3 Audit result

The preload is not an innocuous acceleration parameter. It materially determines the stock path and the basin of the local search. Zero preload does not bootstrap to a comparable solution, high preload can itself satisfy the CV rule, and 0.70 is neither unique nor numerically dominant.

**Classification: code-only structural warm start / finite-horizon boundary condition.**

### 6.4 Reference rule

There is no source-justified universal warm-start percentage.

For the reproducible reference demonstration, retain `0.70` only as the named preset

`warm_start_policy = historical_matrix_warm_start`

so that the reconstruction does not smuggle in a new initializer. In reconciled mode the nonzero preload must propagate with the exact stock recurrence and its value must be machine-visible and configurable.

A zero warm start is not equivalent to the historical matrix procedure. A future endogenous feasible initializer is allowed only as a separately specified reconstruction extension.

## 7. C26: multi-good additional-capital update

Historical `csvplan.jl` uses

`additional_capital = current_stock * scale_increment`.

The verified text gives the economic purpose of the correction but does not print a unique multi-good matrix update.

The C26 audit compared:

- historical stock-proportional update;
- a Leontief/`C` coefficient-increment reconstruction;
- a required-stock-gap reconstruction.

Results:

| C26 rule | mean H | CV | min H |
|---|---:|---:|---:|
| historical stock-proportional | 0.498578600 | 0.037022495 | 0.433778848 |
| coefficient increment | 0.502157617 | 0.038475276 | 0.436141212 |
| required-stock gap | 0.337716070 | 0.328955630 | 0.172411440 |

The coefficient reconstruction improves mean and minimum Harmony but worsens CV; it does not strictly dominate. The required-gap version fails to admit the first transfer. Performance therefore supplies no basis for silently replacing the executable witness.

**Source status: indeterminate. Reference implementation decision: retain the historical stock-proportional update as `historical_matrix_specialization`.**

This is a provenance-labelled implementation specialization, not a theoretical New Harmony invariant. Alternative C26 formulas remain experimental profiles.

## 8. Numerical controls

### 8.1 Epsilon

Historical matrix preset:

`epsilon = 0.25 / depreciation_horizon`.

Printed first suggestion:

`epsilon = 1 / (1 + 1/Delta)`.

Expose epsilon through named policy plus numeric resolved value. Performance interaction does not identify an authorial optimum.

### 8.2 Harmony CV threshold

The text says termination below “some threshold”. Matrix `.034` and scalar `.01` are implementation values. Expose `harmony_cv_threshold`; `.034` is only the historical matrix preset.

### 8.3 Maximum iterations

Expose `max_iterations` as a computational safeguard. `3000` is the historical matrix preset.

Every result must report accepted moves, attempted moves/candidates, stop reason, CV threshold, epsilon and max-iteration value.

## 9. Depreciation horizon

`depreciation_horizon = 14` is a demonstration/planning-window value consistent with the Chapter 6 finite-horizon example. Actual stock depreciation remains cell-specific.

Expose the horizon. Do not replace heterogeneous depreciation rates by `1/14` merely because the shadow window is fourteen years.

## 10. Profiles

### 10.1 Historical matrix replay

Implemented by `legacy.py`; preserve the executable witness exactly, including quirks required for replay:

- warm start 0.70 with historical propagation;
- `repeat_last` shadow continuation;
- historical sequential destination/stop semantics;
- inverse-depreciation default off;
- epsilon `.25/H`;
- CV threshold `.034`;
- maximum iteration counter `3000`.

### 10.2 Reference reconciled profile

Fixed source-adjudicated core:

- vector-correct investment/net-output accounting;
- all positive-target products in robust annual Harmony;
- candidate-state non-negativity;
- exact stock/depreciation chronology;
- global-lowest destination;
- preceding sources only;
- best positive source by total/mean-Harmony gain;
- accepted moves strictly improve total/mean Harmony;
- Leontief within-period accounting and physical capital/labour feasibility.

Provenance-labelled reproducibility controls:

- `warm_start_policy = historical_matrix_warm_start`, reference level `0.70`, configurable;
- `continuation_policy = repeat_last` for the reference demonstration, configurable;
- `epsilon_policy = historical_matrix` for the reference demonstration, configurable;
- `harmony_cv_threshold = 0.034` and `max_iterations = 3000` only as declared historical numerical presets;
- `depreciation_horizon = 14` only as declared demonstration preset;
- `capital_update_policy = historical_matrix_specialization` for C26;
- explicit `blocked_destination_policy`.

A reconciled result is invalid for publication if these provenance fields are absent.

## 11. Numerical checkpoints

Historical baseline:

- mean H `0.483594243`;
- CV `0.048835808`;
- min H `0.402582327`.

P3 cumulative source-reconciled checkpoint, with historical 70% preload and matrix epsilon held fixed during interaction testing:

- mean H `0.498578600`;
- CV `0.037022495`;
- min H `0.433778848`.

P3 strictly dominates the historical baseline on these three metrics, but the result remains preload-sensitive.

The C14 historical-timing sweep shows 0.80 strictly dominating 0.70 on this dataset. The decoupled audit produces different best preload values for mean, CV and minimum Harmony. These findings establish that 0.70 is not an identified optimum; they do not authorize retuning the reference preset.

## 12. Acceptance gate before E/F

Source/code adjudication is complete enough to implement the reference profile. E/F remain frozen until the implementation gate passes:

1. `csvplan.jl ↔ legacy.py` historical replay remains green.
2. The reference reconciled module implements this specification rather than the older provisional `faithful.py` controller.
3. Provenance fields for warm start, continuation, epsilon, threshold, max iterations, horizon, C26 and blocked-destination policy are machine-visible.
4. Direct tests cover vector accounting, all-product robust Harmony, candidate positivity, exact depreciation and global-lowest destination.
5. C26 stock-proportional retention has a regression/oracle test and experimental alternatives remain separate.
6. The full unit-test and numerical-comparison workflows pass from the final reference-reconciled commit.

Only after this gate may the reference controller be ported into E. F remains downstream of the regenerated E baseline.
