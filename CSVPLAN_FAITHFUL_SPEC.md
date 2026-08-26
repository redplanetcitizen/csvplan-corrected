# csvplan reconstruction specification

> **STATUS: AUDITED BUT NOT YET FINAL.** The residual code-only choices are now adjudicated. The remaining core-controller question is C26, the multi-good additional-capital update, plus the engineering question of an endogenous feasible initializer. Until those are closed, `faithful.py` is an experimental reconstruction and must not be described as the definitive Cockshott implementation.

## 1. Objects kept distinct

The repository contains three analytically different objects.

1. **Cockshott `csvplan.jl` original**: immutable historical prototype sample.
2. **`legacy.py`**: verified Python numerical replay of the historical prototype.
3. **reconciled reconstruction**: a source-adjudicated implementation target that corrects confirmed defects and follows explicit textual rules where the matrix prototype conflicts with them.

The valid historical relation is:

`Cockshott csvplan.jl ≈ Python legacy.py`.

A different numerical result from the reconciled reconstruction is not evidence of greater fidelity by itself. Every divergence must be tied to an adjudicated source/code decision.

## 2. Evidence and precedence

The reconstruction uses these witnesses:

- Chapter 6, `Theory of Optimal Planning`;
- `Design for Julia implementation of the New Harmony algorithm`;
- scalar `harmony2.jl` where it illuminates the written procedure;
- matrix `csvplan.jl` as executable historical witness.

The standalone operational document previously remembered as `Using csvplan.jl` is not present in the current verified source bundle and contributes no evidence until recovered.

Decision precedence is row-specific, not a blanket hierarchy:

- explicit text plus compatible local semantics prevail over a confirmed programming defect;
- explicit text prevails for a direct algorithmic prescription when the matrix prototype implements a conflicting active path, while the historical path remains replayable;
- code-only values are preserved in the historical profile but are not promoted to theoretical constants;
- unresolved choices are labelled reconstruction choices, not silently attributed to Cockshott.

The current adjudication is recorded in `CSVPLAN_RECONCILIATION_MATRIX.md`, `CSVPLAN_ADJUDICATION_STATUS.md`, and `CSVPLAN_RESIDUAL_CODE_ONLY_ADJUDICATION.md`.

## 3. Mathematical core fixed by the sources

### 3.1 Fractional Harmony

Use

`h(x) = x / (1.1 + x)`

on the economically relevant domain.

For a year `t`, compute fulfilment by product from net/final social output and positive plan targets. Robust annual Harmony is

`H_t = min_i h(f[t,i] / g[t,i])`

over products with positive targets. Labour is a constraint, not a final product in the Harmony minimum.

### 3.2 Within-period Leontief calculation

For final demand `f_t`, gross output is

`o_t = (I - A)^-1 f_t`.

Investment produced in year `t` belongs to final demand in that year and becomes productive capital from the start of year `t+1`.

### 3.3 Capital stocks

Use source-product × user-sector capital requirement matrix `C` and time-indexed stock tensor `S[t,i,j]`.

The stock identity is

`S[t+1,i,j] = (1 - d[i,j]) * S[t,i,j] + I[t,i,j]`.

Capital feasibility is cell-specific. Labour provides an additional aggregate constraint and the most restrictive condition determines feasible scale.

### 3.4 Source-to-destination investment

Investment shifted from a source year to a later destination must be adjusted so that the amount arriving at the destination is the required surviving capital after intervening depreciation. Candidate transfers must be evaluated on the **candidate** state, and no accepted transfer may create negative net final goods in the source year.

An accepted move must strictly improve total/mean Harmony within numerical tolerance.

## 4. Intertemporal destination rule

Design, Chapter 6, and scalar `harmony2.jl` explicitly prescribe selecting the year with the **lowest Harmony**. The active sequential-below-mean scan in `csvplan.jl` is therefore historical behavior, not the source-reconciled destination rule.

The reconciled controller must begin an iteration from the globally lowest-Harmony year.

If that year has no positive transfer, the text does not uniquely specify the completion rule. A reconciled implementation may inspect subsequent years in ascending Harmony order and terminate only after a full failed pass. This is an explicit `our_choice` local-search certificate and must be identified as such in provenance output.

## 5. Finite planning horizon

The published/input horizon is `T`. The computational horizon may extend beyond `T` to prevent artificial terminal disinvestment. Chapter 6 explicitly gives the example of a good five-year plan evaluated over a nineteen-year window when industrial fixed capital has a fourteen-year horizon.

This source-supported finite-horizon principle does **not** uniquely determine the economic data in the shadow years.

Therefore a reconstructed solver must distinguish:

- `published_horizon`;
- `computational_horizon`;
- `continuation_policy`.

`repeat_last` reproduces the matrix prototype's policy of holding the last explicit targets and labour constant. It is a historical/reproducibility policy, not a theoretical invariant. Other continuation scenarios must be supplied explicitly and recorded.

## 6. Preliminary investment / warm start

### 6.1 Historical fact

Matrix `csvplan.jl` sets

`initialinvestmentlevel = 0.7`

and preassigns 70% of replacement investment in every nonterminal computational year before iterative search.

### 6.2 Source status

The available nine-step New Harmony procedure does not state a uniform preliminary replacement fraction. It initializes the stock path by depreciation and then schedules investment endogenously through the intertemporal correction step.

### 6.3 Audit result

The 70% rule is not an innocuous speed optimization. The local search is materially path-dependent on the preliminary capital schedule. Zero or low preload does not bootstrap to a comparable full-horizon state; high preload can itself trigger the CV stopping rule. The value 0.70 is also not uniquely optimal on the demonstration problem.

### 6.4 Specification

The warm start has the final classification:

**code-only structural initialization / finite-horizon boundary condition.**

Consequences:

- historical replay: use 0.70 exactly and historical propagation;
- reconciled reconstruction: warm-start policy must be explicit and provenance-labelled;
- no fixed percentage may be described as a Cockshott theoretical constant;
- if a nonzero preliminary schedule is used in reconciled mode, propagate it with the exact stock recurrence;
- a zero warm start must not be advertised as equivalent to the matrix prototype, because the current local search does not reliably bootstrap from it;
- a future endogenous initializer is permitted only as a separately specified and audited reconstruction subproblem.

There is therefore **no scientifically justified universal numeric default for the reconciled warm-start percentage at this checkpoint**.

## 7. Numerical controls

### 7.1 Epsilon

The historical matrix preset is

`epsilon = 0.25 / depreciation_horizon`.

The text gives

`epsilon = 1 / (1 + 1/Delta)`

only as a first suggestion. For a depreciation rate `Delta = 1/14`, this gives `1/15`.

Both are named presets, not universal constants:

- `historical_matrix`: `0.25/H`;
- `text_first_suggestion`: `1/(1+1/Delta)`;
- explicit numeric epsilon: caller-supplied.

The audit found interaction effects, so performance cannot be used to infer authorial priority.

### 7.2 Harmony CV threshold

The text specifies termination below “some threshold”. Matrix `.034` and scalar `.01` are implementation values.

Expose `harmony_cv_threshold`. Historical matrix replay uses `.034`. A reconciled run must report the selected threshold.

### 7.3 Maximum iterations

Expose `max_iterations` as a computational safeguard. Historical matrix replay uses `3000`. It is not part of the economic model.

Every result must report accepted moves, attempted moves/candidates, stop reason, CV threshold, epsilon, and maximum-iteration setting.

## 8. Depreciation horizon

`depreciation_horizon = 14` is a documented demonstration/planning-window value, not a universal depreciation law. The actual capital-stock recurrence uses the cell-specific depreciation matrix.

Expose the horizon as a parameter. The historical/demo profile uses 14. Never replace heterogeneous depreciation rates by `1/14` merely because the shadow window is fourteen years.

## 9. Profiles

### 9.1 Historical matrix replay profile

This profile is implemented by `legacy.py` and preserves the original executable witness, including behavior that the source audit later identifies as defective or conflicting when necessary for numerical replay.

Key operational controls:

- preliminary warm start = 0.70;
- historical preliminary stock propagation;
- shadow continuation = `repeat_last`;
- active historical matrix destination/stop semantics;
- inverse-depreciation default off;
- epsilon = `0.25/H`;
- CV threshold = `.034`;
- maximum iteration counter = `3000`.

### 9.2 Reconciled reconstruction profile

Source-supported/adjudicated invariants:

- vector-correct net-output accounting;
- all positive-target products included in robust annual Harmony;
- candidate-state non-negativity;
- exact stock/depreciation chronology;
- global-lowest destination;
- preceding source years only;
- accepted move must increase total/mean Harmony;
- Leontief within-period accounting and physical capital/labour feasibility.

Explicit, provenance-labelled controls:

- `warm_start_policy` and any warm-start level;
- `continuation_policy` for shadow years;
- `epsilon_policy` / epsilon;
- `harmony_cv_threshold`;
- `max_iterations`;
- `depreciation_horizon`;
- `blocked_destination_policy`, where `ranked_full_pass` is currently an `our_choice` completion rule.

A reconciled result is invalid for publication if these provenance fields are absent.

## 10. Results supporting the profile split

Historical baseline:

- mean H `0.483594243`;
- CV `0.048835808`;
- minimum H `0.402582327`.

P3 cumulative audit, retaining 70% preload and matrix epsilon while applying adjudicated accounting/depreciation changes and global-lowest destination:

- mean H `0.498578600`;
- CV `0.037022495`;
- minimum H `0.433778848`.

P3 strictly dominates the historical baseline on these three metrics.

The preload sensitivity study then shows why this does not identify the 70% value. With historical preliminary timing, preload 0.80 reaches mean H `0.500223`, CV `0.035534`, minimum H `0.442186`, strictly dominating 0.70. With exact timing and additional decoupling controls, preload 0.90 maximizes tested mean H while 1.20 minimizes CV and maximizes worst-year Harmony, but the latter stops after one endogenous move. The preload is therefore a path/boundary parameter, not a recovered optimum.

## 11. Remaining open core issue: C26

The available source material does not print a unique multi-good formula for the additional-capital matrix used to move the destination toward mean Harmony.

Historical `csvplan.jl` uses a construction proportional to current destination stock:

`additional_capital = current_stock * scale_increment`.

A formula such as

`max(C * target_gross - current_stock, 0)`

may be economically attractive, but at present it is a reconstruction unless a primary source is found. C26 therefore remains `INDETERMINATE / IMPLEMENTATION SPECIALISATION`.

No default solver should be promoted as final until C26 is either retained explicitly as the historical specialization or replaced by a separately justified reconstruction with comparison evidence.

## 12. Acceptance gate before E/F

Before modifying the empirical E repository, csvplan must satisfy all of the following:

1. `csvplan.jl ↔ legacy.py` historical replay remains green.
2. Confirmed accounting, positivity, and depreciation corrections have direct tests.
3. Destination/global-lowest behavior has a source-conformity test.
4. Warm-start, shadow continuation, epsilon, threshold, horizon, and blocked-destination policies are emitted as provenance rather than hidden defaults.
5. C26 has an explicit adjudication and test.
6. The full csvplan test suite and numerical comparison workflows pass.

Only after this gate may the reconciled controller be ported into E. F remains downstream of the regenerated E baseline.
