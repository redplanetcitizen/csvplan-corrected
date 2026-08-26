# csvplan adjudication status

## Purpose and current state

This file consolidates the source/code audit after the reconciliation matrix, Stage A, Stage B, the depreciation-timing audit, the P0-P4 composite audit, the residual code-only audit, and the warm-start decoupling audit.

Paul Cockshott's original `csvplan.jl` remains the immutable historical prototype sample. `legacy.py` remains its verified numerical replay. No replacement solver is yet designated canonical. The experimental module currently named `faithful.py` must continue to be treated as a reconstruction under audit until the remaining indeterminate controller issue C26 and the initialization policy are resolved.

The detailed disposition of residual executable choices is in `CSVPLAN_RESIDUAL_CODE_ONLY_ADJUDICATION.md`.

## 1. Confirmed implementation defects

### C13: scalar linear indexing in investment subtraction

`investmentsByTypeandYear` returns a matrix `[year, sourceindustry]`, but the historical net-output update indexes it with one Julia index and broadcasts the resulting scalar over the product vector. The textual model defines vector-valued final consumption as output less accumulation and productive consumption.

**Status: CONFIRMED INDEXING DEFECT.**

### C02/C28: an actual product is dropped from annual robust Harmony

The labour column has already been removed before `harmonyarrayofarrays[i][1:end-1]` is evaluated. The extra slice therefore removes a product despite the adjacent comment saying that labour is being ignored.

**Status: CONFIRMED INDEXING DEFECT.**

### C12: positivity is tested on the pre-transfer scenario

The text requires rejection of a proposed investment if the proposal would produce negative net goods in the source year. The matrix code builds a candidate scenario but tests the old scenario.

**Status: CONFIRMED WRONG-OBJECT CHECK.**

### C11b/C16: depreciation timing

The stated stock recurrence makes investment produced in year `t` available in `t+1`; later stocks contain the amount surviving the corresponding full depreciation periods. The historical helper leaves the amount unchanged for one extra period and the latent inverse-depreciation path has the analogous offset.

**Status: HIGH-CONFIDENCE TIME-INDEXING DEFECT.**

The justification is the stock identity, not ex post Harmony performance.

## 2. Direct text/code conflicts

### C05: destination year

Design, Chapter 6, and scalar `harmony2.jl` select the year with the **lowest Harmony**. Matrix `csvplan.jl` contains such a function but the active loop instead scans sequentially and acts on every year below the current mean.

**Status: DIRECT TEXT/CODE CONFLICT.**

The one-factor audit additionally found that global-lowest strictly dominates the active historical matrix scan on the demonstration data. In the cumulative P3 reconstruction it is also the major positive interaction: P3 reaches mean H `0.498578600`, CV `0.037022495`, and minimum H `0.433778848`, all better than the historical baseline.

For the source-reconciled core, the explicit textual rule prevails: **global lowest Harmony**.

### C11a: source-to-destination depreciation disabled

Design and Chapter 6 explicitly require earlier investment to arrive at the destination depreciated. Scalar `harmony2.jl` implements inverse depreciation. Matrix `csvplan.jl` defines the helper but disables it by default.

**Status: DIRECT TEXT/CODE CONFLICT.**

For the source-reconciled core, exact depreciation consistent with the stock recurrence prevails. The disabled historical flag remains part of replay only.

## 3. Residual code-only choices now adjudicated

### C14: preliminary 70% replacement schedule

`initialinvestmentlevel=0.7` preassigns 70% of `caps .* dep` before the iterative search. The available nine-step textual algorithm does not state this initialization. Chapter 6 instead starts from depreciated initial stocks and schedules investment endogenously in Step 8.

The residual sweep and warm-start decoupling audit resolve its operational role:

- zero preload does not allow the current local controller to bootstrap to a comparable full-horizon solution;
- the final state changes strongly with preload level even after exact preliminary timing, ranked fallback, and a mandatory search pass;
- 0.70 is neither numerically unique nor dominant;
- high preload can itself trigger the CV stopping rule after zero or one endogenous move;
- applying the preload only to published years performs much worse, while shadow-only preload can generate physical pathologies.

**Status: CODE-ONLY STRUCTURAL WARM START / FINITE-HORIZON BOUNDARY CONDITION. THE VALUE 0.70 IS NOT A THEORETICAL CONSTANT.**

Historical replay keeps 0.70 exactly. A reconciled reconstruction must expose the warm start and its provenance. If a nonzero warm start is used, its stock propagation must follow the exact recurrence. No alternative fixed percentage is promoted to canonical status by the performance sweep.

An endogenous initializer would be a new reconstruction subproblem, not a recovered Cockshott rule.

### C21: continuation targets and labour

The finite-horizon extension is source-supported, including the Chapter 6 example of optimising a five-year published plan over nineteen years when the industrial capital horizon is fourteen years. The rule by which every shadow target and labour row is generated is not uniquely stated in the verified passage. `csvplan.jl` repeats the last explicit row.

±10% shadow-only perturbations materially change full-horizon and published-horizon results.

**Status: CODE-ONLY BOUNDARY-CONDITION POLICY.**

Historical replay uses `repeat_last`. A reconciled implementation must expose continuation policy explicitly; `repeat_last` can be a reproducibility option but must not be called a theoretical invariant.

### C23/C24: termination after a blocked destination

The historical matrix controller terminates globally when the current destination has no preceding source with positive overall-Harmony gain. A ranked-fallback audit finds another positive move after the globally worst year becomes blocked. The numerical difference is small, but the logical point is decisive: failure at one destination does not prove global local optimality.

**Status: CODE-ONLY STOPPING SPECIALISATION.**

Historical replay keeps first-blocked termination. A reconciled controller may use an ordered full-pass certificate: try destinations in ascending Harmony order and stop only if the full pass finds no improving move. That completion rule is explicitly **OUR CHOICE**, not attributed to Cockshott.

### C29: CV threshold and maximum iteration count

Matrix `csvplan.jl` uses `.034` and `3000`; the verified text says only “some threshold” and does not provide universal matrix constants. The audit shows that CV can materially change the endpoint and that `maxiter` is a computational safeguard which becomes binding in difficult preload regimes.

**Status: CODE-ONLY PARAMETERISATION.**

Expose both. Historical replay uses `.034/3000`; no general implementation may describe those numbers as theoretical constants.

### C07: epsilon

Matrix `csvplan.jl` uses `.25/depreciationhorizon`. The text gives `1/(1+1/Delta)` only as a first suggestion and Cockshott's executable witnesses use different operational scalings. The first-suggestion value improves the historical baseline in isolation but worsens P3 on mean/CV when added cumulatively.

**Status: TUNING PARAMETER / TEXTUAL VARIANT.**

Expose epsilon. Preserve the matrix value as a historical preset and the printed formula as a separately named textual-suggestion preset.

### C22: depreciation horizon 14

Chapter 6 uses a fourteen-year industrial-capital horizon in its finite-horizon example, while the code itself comments that fourteen is hoped to be long enough. Actual depreciation remains cell-specific.

**Status: DEMONSTRATION PARAMETER / IMPLEMENTATION SPECIALISATION.**

Expose the computational horizon. Fourteen is a reproducible example value, not a universal depreciation law.

## 4. Source-supported / legitimate implementation specialisations

The following remain admissible without being described as bug corrections:

- fractional Harmony `H(x)=x/(1.1+x)`;
- robust annual Harmony as the minimum per-product Harmony over final goods with positive targets;
- Leontief inversion within a year;
- cell-specific capital feasibility followed by labour feasibility;
- source years restricted to dates preceding the destination;
- selection of the source by greatest positive total/mean-Harmony gain in the matrix path;
- full candidate-scenario re-evaluation rather than the cheaper labour-value approximation discussed in Design;
- fixed `A` over the demonstration horizon, with time-varying technology recognized as a possible extension;
- a computational horizon extending past the published plan so terminal investment is not artificially discouraged.

## 5. Performance checkpoints

Historical `csvplan.jl` / `legacy.py` baseline:

- mean H `0.483594243`
- CV `0.048835808`
- min H `0.402582327`
- 331 accepted moves
- stop: no positive transfer.

Cumulative source-reconciled P3, retaining the 70% historical preload and matrix epsilon during the interaction audit:

- mean H `0.498578600`
- CV `0.037022495`
- min H `0.433778848`.

P3 strictly dominates the historical baseline on all three agreed metrics. This is performance evidence, not by itself authorship evidence. Its substantive changes are independently justified by the source/code adjudication.

The C14 sweep confirms that this P3 endpoint remains preload-dependent. Under historical preliminary timing, 0.80 gives mean H `0.500223`, CV `0.035534`, min H `0.442186`, which strictly dominates 0.70. This does **not** justify changing the historical or theoretical default to 0.80; it proves that 0.70 is not an identified optimum.

Under the warm-start decoupling audit, with exact preliminary timing, ranked fallback and one mandatory search pass, 0.90 gives the best tested mean H `0.498483`, whereas 1.20 gives the best tested CV `0.025040` and minimum H `0.450413`, but after only one endogenous move. This further demonstrates that preload and convergence are structurally entangled.

All audit workflows reported here completed successfully and the repository's 18-test suite passed after the residual and warm-start audits.

## 6. Profiles fixed by the adjudication

### Historical replay

Use `legacy.py` and preserve:

- 0.70 preliminary replacement;
- historical preliminary propagation;
- repeat-last shadow continuation;
- historical active destination/stop controller;
- epsilon `.25/H`;
- `.034/3000` stopping parameters;
- legacy quirks required for numerical replay.

### Reconciled reconstruction

The source-supported core is now:

- vector-correct investment accounting;
- all-product robust annual Harmony;
- post-candidate non-negativity;
- exact capital-stock/depreciation timing;
- global-lowest destination;
- positive total-Harmony improvement for accepted moves.

The following must remain provenance-labelled parameters or completion policies rather than inferred Cockshott constants:

- warm-start/preliminary investment;
- shadow continuation;
- epsilon;
- CV threshold;
- maximum iterations;
- depreciation horizon;
- full-pass fallback after a blocked destination.

## 7. Remaining open item before a final reconciled solver

The main unresolved core-controller item is **C26**: the multi-good formula for translating the desired move toward mean Harmony into an additional-capital matrix. The historical matrix uses `current_stock * scale_increment`. The verified text specifies the economic requirement but does not print a unique matrix update formula. Replacing the Julia expression with `C * target_gross - current_stock`, or another construction, would presently be a reconstruction choice rather than a source correction.

The second unresolved engineering item is endogenous initialization. The residual audit has resolved the epistemic status of 70%, but it has also shown that the current local search cannot simply start from zero and be assumed equivalent. If we want a reconciled solver with no arbitrary fixed preload, we must design and audit a separate feasible initialization procedure.

Until those two issues are addressed, `faithful.py` remains experimental and E/F remain frozen.
