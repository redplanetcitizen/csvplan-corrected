# csvplan adjudication status

## Purpose and current state

This file consolidates the source/code audit after the reconciliation matrix, Stage A, Stage B, depreciation timing, the P0-P4 composite audit, the residual code-only audit, the warm-start decoupling audit, and the C26 capital-update audit.

Paul Cockshott's original `csvplan.jl` remains the immutable historical prototype sample. `legacy.py` remains its verified numerical replay. The audits now support a **reference reconciled profile**, but this profile must preserve explicit provenance for every code-only or reconstructed completion rule. It is not legitimate to collapse the historical prototype, the printed algorithm, and our completion choices into a single undifferentiated object called “Cockshott's algorithm”.

Detailed decisions are in `CSVPLAN_RESIDUAL_CODE_ONLY_ADJUDICATION.md` and `CSVPLAN_C26_ADJUDICATION.md`.

## 1. Confirmed implementation defects

### C13: scalar investment subtraction

`investmentsByTypeandYear` returns a matrix `[year, sourceindustry]`, but the historical net-output update uses a single Julia index and broadcasts the resulting scalar over the product vector.

**Status: CONFIRMED INDEXING DEFECT.**

### C02/C28: last actual product dropped from robust Harmony

Labour has already been removed before `harmonyarrayofarrays[i][1:end-1]` is evaluated, so the extra slice removes a product.

**Status: CONFIRMED INDEXING DEFECT.**

### C12: positivity checked on the wrong scenario

The text requires rejection when the proposed transfer makes source-year net goods negative, but the matrix prototype checks the pre-transfer state.

**Status: CONFIRMED WRONG-OBJECT CHECK.**

### C11b/C16: depreciation timing

The stated recurrence makes investment produced in year `t` available in `t+1`; later stocks contain the amount surviving the corresponding depreciation periods. The historical propagation/inverse helpers contain an extra-period offset against this identity.

**Status: HIGH-CONFIDENCE TIME-INDEXING DEFECT.**

The correction is justified by the stock identity, not by whichever variant scores better ex post.

## 2. Direct text/code conflicts

### C05: destination year

Design, Chapter 6, and scalar `harmony2.jl` select the year with the **lowest Harmony**. Matrix `csvplan.jl` contains a minimum-Harmony helper but its active loop scans sequentially and acts on below-mean years.

**Status: DIRECT TEXT/CODE CONFLICT.**

The source-reconciled core uses **global lowest Harmony**. The historical sequential scan remains replayable only in the historical profile.

### C11a: source-to-destination depreciation disabled

Design and Chapter 6 explicitly require earlier investment to arrive at the destination depreciated. The matrix prototype defines an inverse-depreciation helper but disables it by default.

**Status: DIRECT TEXT/CODE CONFLICT.**

The source-reconciled core uses exact depreciation consistent with the stock recurrence.

## 3. Residual code-only choices

### C14: preliminary 70% replacement schedule

`initialinvestmentlevel=0.7` preassigns 70% of replacement investment before iterative search. The available nine-step textual procedure does not state this fixed fraction.

The residual sweep and warm-start-decoupling audit show that the preload materially determines the capital-stock path and the basin of the local search. Zero preload does not bootstrap to a comparable solution; high preload can satisfy the CV stopping rule before meaningful search; 0.70 is neither unique nor numerically dominant.

**Status: CODE-ONLY STRUCTURAL WARM START / FINITE-HORIZON BOUNDARY CONDITION. THE VALUE 0.70 IS NOT A THEORETICAL CONSTANT.**

Historical replay keeps 0.70. The reference reconciled demonstration may also use the historical 0.70 witness so that no new initializer is smuggled into the model, but it must label it `historical_matrix_warm_start`, propagate it with the exact stock recurrence, and expose it as a replaceable parameter. No performance sweep is allowed to promote 0.80, 0.90, or another value to an authorial default.

An endogenous initializer remains a legitimate future extension, but it would be a new reconstruction subproblem rather than a recovered Cockshott rule.

### C21: shadow targets and labour

The longer computational horizon is source-supported. The policy of repeating the last explicit target/labour row through every shadow year is not uniquely prescribed in the verified passage, and ±10% shadow perturbations materially change both full-horizon and published-period results.

**Status: CODE-ONLY BOUNDARY-CONDITION POLICY.**

Historical replay uses `repeat_last`. The reference reconciled demonstration may use the same policy for reproducibility, but the policy must be emitted as provenance and remain configurable.

### C23/C24: first blocked destination terminates globally

A ranked fallback audit found an additional positive transfer after the globally worst year became blocked. Therefore failure at one destination is not a proof that no improving move exists elsewhere.

**Status: CODE-ONLY STOPPING SPECIALISATION.**

Historical replay keeps first-blocked termination. A reconciled controller may use an ascending-Harmony full failed pass as a local-search certificate, but that completion rule is explicitly **OUR CHOICE**.

### C29: CV threshold and maximum iteration count

Matrix `.034` and `3000` are implementation constants. The text gives no universal numerical pair, and the audit shows the CV threshold can materially determine the endpoint.

**Status: CODE-ONLY PARAMETERISATION.**

Expose both. `.034/3000` is the historical matrix preset, not a theoretical constant.

### C07: epsilon

Matrix `csvplan.jl` uses `.25/depreciationhorizon`. The printed `1/(1+1/Delta)` expression is explicitly only a first suggestion. The two values interact differently with the reconciled controller.

**Status: TUNING PARAMETER / TEXTUAL VARIANT.**

Expose epsilon. Keep named presets for `historical_matrix` and `text_first_suggestion`; do not infer authorial priority from performance.

### C22: depreciation horizon 14

Chapter 6 uses a fourteen-year industrial-capital horizon in its finite-horizon example, while actual stock depreciation remains cell-specific.

**Status: DEMONSTRATION PARAMETER / IMPLEMENTATION SPECIALISATION.**

Expose the computational horizon. Fourteen is a reproducible example value, not a universal depreciation law.

## 4. C26: multi-good additional-capital formula

The historical matrix prototype converts the desired destination adjustment into

`additional_capital = current_stock * scale_increment`.

The verified text states the economic objective but does not print a unique multi-good matrix formula for this step.

The C26 audit held P3 fixed and compared three formulas:

| rule | mean H | CV | min H | accepted |
|---|---:|---:|---:|---:|
| historical stock-proportional | 0.498578600 | 0.037022495 | 0.433778848 | 43 |
| coefficient increment via Leontief and `C` | 0.502157617 | 0.038475276 | 0.436141212 | 37 |
| required-stock-gap reconstruction | 0.337716070 | 0.328955630 | 0.172411440 | 0 |

The coefficient-increment reconstruction raises mean and minimum Harmony but worsens CV, so it does not strictly dominate the historical rule on the agreed three metrics. The required-stock-gap formulation cannot make the first transfer under the tested controller. Both alternatives diverge from the historical rule on the first correction.

**Source status: INDETERMINATE. Reference implementation decision: CLOSED.**

The reference reconciled profile retains the historical stock-proportional rule as `historical_matrix_specialization`, because it is the only directly witnessed executable multi-good rule and no primary text supplies a unique replacement. This retention is an implementation-provenance decision, not a claim that the formula is a theoretical New Harmony invariant.

The coefficient-increment construction remains an experimental reconstruction and may be studied separately. It must not silently replace the matrix witness.

## 5. Source-supported core and legitimate specialisations

The reference reconciled core now fixes:

- fractional Harmony `H(x)=x/(1.1+x)`;
- annual robust Harmony as the minimum over all positive-target final products;
- Leontief inversion within a year;
- vector-correct final/net-output accounting;
- candidate-state non-negativity;
- cell-specific capital feasibility plus labour feasibility;
- exact stock/depreciation chronology;
- destination = global lowest Harmony;
- source years strictly preceding the destination;
- source selection by greatest positive total/mean-Harmony gain in the matrix path;
- accepted moves must improve total/mean Harmony;
- C26 stock-proportional update retained as an explicitly labelled matrix-prototype specialisation;
- a computational horizon extending past the published plan.

## 6. Performance checkpoints

Historical `csvplan.jl` / `legacy.py` baseline:

- mean H `0.483594243`;
- CV `0.048835808`;
- min H `0.402582327`;
- 331 accepted moves;
- stop: no positive transfer.

P3, retaining 70% preload and matrix epsilon while applying adjudicated accounting/depreciation corrections and global-lowest destination:

- mean H `0.498578600`;
- CV `0.037022495`;
- min H `0.433778848`.

P3 strictly dominates the historical baseline on the three agreed metrics. This is supporting performance evidence, not the basis for the source adjudication.

For C14, historical-timing preload 0.80 strictly dominates 0.70 on the demonstration data, while the decoupled audit gives different best levels for mean, CV, and worst-year Harmony. That is evidence that 0.70 is not identified as an optimum, not a reason to retune the reference profile.

The C26 workflow reproduced the P3 oracle exactly for the historical stock-proportional rule and the repository's 18-test suite passed.

## 7. Profiles fixed by the audit

### Historical replay profile

Use `legacy.py` and preserve the executable witness exactly, including:

- preliminary replacement = 0.70;
- historical preliminary propagation;
- `repeat_last` shadow continuation;
- active historical sequential destination/stop semantics;
- inverse-depreciation default off;
- epsilon `.25/H`;
- CV threshold `.034`;
- maximum iteration counter `3000`;
- legacy quirks required for numerical replay.

### Reference reconciled profile

Apply the source-adjudicated corrections and explicit text rules, while carrying the unresolved-by-text executable choices with visible provenance:

- warm start: `historical_matrix_warm_start`, level 0.70 for the reproducible reference demonstration, exact propagation, configurable;
- shadow continuation: `repeat_last` for the reproducible reference demonstration, configurable;
- epsilon: `historical_matrix` preset unless another preset is explicitly requested;
- CV threshold/max iterations: historical preset only as declared numerical controls;
- C26: `historical_matrix_specialization`;
- blocked-destination completion: either historical first-blocked or an explicitly labelled `our_choice` ranked full pass; the default reference run must state which is used.

Every published result must emit these provenance fields. Hidden defaults are not acceptable.

## 8. Gate before E/F

The source/code adjudication stage is now closed enough to build the reference reconciled solver. The 70% issue has been resolved epistemically and operationally; it does not need to be eliminated before proceeding. C26 has also been closed as a retention decision rather than replaced by an unsupported reconstruction.

Before modifying E, the csvplan repository must still pass the implementation gate:

1. historical `csvplan.jl ↔ legacy.py` replay remains green;
2. the reference reconciled module actually implements the profile above rather than the older provisional `faithful.py` semantics;
3. provenance fields for warm start, shadow continuation, epsilon, thresholds, horizon, C26 and blocked-destination policy are machine-visible in output;
4. source-conformity tests cover global-lowest destination, all-product Harmony, candidate positivity and exact depreciation;
5. the full numerical and unit-test workflows pass from the final reference-reconciled commit.

E/F remain frozen until this implementation gate is met.
