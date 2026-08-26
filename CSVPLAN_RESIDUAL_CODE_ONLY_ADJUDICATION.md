# csvplan residual code-only adjudication

## Scope

This document closes the audit of the residual `csvplan.jl` choices that are executable but not uniquely prescribed by the available New Harmony text. It follows the reconciliation matrix, Stage A, Stage B, the depreciation-timing audit, the P0-P4 composite audit, the residual code-only sweep, and the warm-start decoupling audit.

It does **not** modify the historical reference. Paul Cockshott's `csvplan.jl` remains the immutable prototype sample and `legacy.py` remains its verified numerical replay. The purpose here is to decide which historical choices may be carried into a reconciled reconstruction, which must be parameterised, and which must be labelled as our own completion rules.

The available Chapter 6 procedure starts from depreciated initial capital stocks, computes feasible goal fulfilment, selects the year with the lowest Harmony, and then schedules investment in at least one previous year. It does not state a preliminary uniform fraction of replacement investment. The same chapter explicitly presents the coefficient-of-variation cutoff only as “some threshold” and the epsilon formula only as a first suggestion. The finite-horizon discussion supports a longer computational window but does not uniquely prescribe how all shadow target and labour rows must be generated.

## Decision table

| ID | Historical `csvplan.jl` choice | Audit result | Final adjudication | Reconciled reconstruction rule |
|---|---|---|---|---|
| C14 | `initialinvestmentlevel = 0.7`, applied as 70% of replacement in all nonterminal computational years | Strong path dependence; 0.70 is neither unique nor dominant. Zero preload cannot bootstrap the local controller reliably. High preload can satisfy the CV rule before meaningful search. Exact-timing and warm-start-decoupling tests do not remove the dependence. | **CODE-ONLY STRUCTURAL WARM START / BOUNDARY CONDITION. 0.70 IS NOT A THEORETICAL CONSTANT.** | No fixed percentage may be attributed to Cockshott's textual algorithm. Historical profile keeps 0.70 exactly. Reconciled profile exposes the warm start explicitly; if nonzero it must obey the exact stock recurrence. A future endogenous initializer may replace it, but that would be a separate reconstruction step and must be audited independently. |
| C21 | Shadow targets and labour repeat the last explicit row | ±10% perturbations of shadow targets/labour materially change both full-horizon and published-horizon results. | **CODE-ONLY BOUNDARY-CONDITION POLICY.** | Historical profile repeats the last row. Reconciled profile makes continuation policy explicit. `repeat_last` may be offered for reproducibility but not described as an invariant of the theory. |
| C23/C24 | Stop the whole search when the selected/current destination admits no positive-gain source | Ranked fallback finds an additional positive transfer on the demonstration problem. The numerical improvement is small, but the historical stop is demonstrably not a proof that no improving move exists elsewhere. | **CODE-ONLY STOPPING SPECIALISATION; HISTORICAL RULE IS PREMATURE AS A GENERAL LOCAL-SEARCH CERTIFICATE.** | Historical profile keeps first-blocked termination. Reconciled profile may try years in ascending Harmony order until a positive move is found and terminate only after a full failed pass. This is **OUR CHOICE**, not a recovered Cockshott rule. |
| C29 | `mincoeff = 0.034`, `maxiter = 3000` | 0.034 can become binding and materially alter the result; 3000 is nonbinding in the P3 demonstration but binds in some low-preload variants. The text gives no universal numerical values. | **CODE-ONLY PARAMETERISATION.** | Expose both values. Historical profile keeps 0.034/3000. Reconciled profile must not present either as theoretical constants. `max_iterations` is a computational safeguard; CV is an economic/numerical stopping tolerance. |
| C07 | `epsilon = 0.25 / depreciationhorizon` | The textual `1/(1+1/Delta)` is explicitly a first suggestion. It improves the historical baseline in isolation but worsens the P3 composite on mean/CV. | **TUNING PARAMETER / TEXTUAL VARIANT.** | Historical profile keeps `0.25/H`. Reconciled profile exposes epsilon. The text formula may be offered as a named `text_first_suggestion`, not as a canonical value. |
| C22 | `depreciationhorizon = 14` | Chapter 6 uses 14 years as the industrial-capital example and recommends 5+14 for a five-year published plan. The code itself treats 14 as an estimate, while depreciation rates remain cell-specific. | **DEMONSTRATION PARAMETER / IMPLEMENTATION SPECIALISATION.** | Keep `depreciation_horizon` configurable. Historical/demo profile uses 14. Do not replace heterogeneous depreciation rates with `1/14`, and do not attribute 14 to an external dataset without a source. |

C26, the matrix formula used to estimate additional capital at the destination, is **not** closed by this document. It is not merely a residual code-only constant: the available text does not print a unique multi-good update formula. It remains `INDETERMINATE / IMPLEMENTATION SPECIALISATION` and requires a separate reconstruction comparison if we intend to replace the historical `current_stock * scale_increment` rule.

## C14: what the 70% actually does

The original question was whether the 70% preliminary schedule is a theoretical part of New Harmony, an accelerator that can be removed after convergence mechanics are corrected, or an arbitrary implementation choice.

The audit rules out the first and third formulations in their simple form.

It is **not a textual part of the nine-step algorithm**. The available Chapter 6 statement initializes the stock path by depreciation and then endogenously schedules investment through Step 8. No uniform 70% preliminary replacement fraction is stated there.

It is also **not an innocuous accelerator**. With the P3 mechanics held fixed, the result changes strongly with the preload. Removing it produces a very poor full-horizon solution; changing its level changes the basin and sometimes the stopping mechanism. Applying 70% only to published years performs much worse than applying it to the entire computational window, while applying it only to shadow years is physically pathological on the demonstration problem. The schedule therefore acts as a capital-stock scaffold across the whole finite horizon.

The value **0.70 itself is not identified**. In the historical-timing sweep, 0.80 strictly dominates 0.70 on full-horizon mean Harmony, CV, and worst-year Harmony. That does not make 0.80 canonical: choosing it would be ex post tuning to one dataset. In the decoupled audit with exact preliminary timing, ranked fallback, and a mandatory search pass, 0.90 has the best mean Harmony among tested levels while 1.20 has the best CV and worst-year Harmony. The ranking therefore depends on the performance criterion and the stopping interaction.

The correct interpretation is:

> **The 70% rule is a code-only warm-start/boundary-condition device on which the matrix prototype's local search materially depends. It is necessary for reproducing the historical run, but neither the existence of a fixed preload nor the value 0.70 is justified as a theoretical invariant by the available sources.**

This means the reconciled implementation cannot silently set the warm start to zero and call that “more faithful”, but it also cannot silently retain 0.70 and call that a Cockshott theorem. The provenance of the initializer must be visible.

## Numerical evidence for C14

### P3 level sweep with historical preliminary timing

| preload | mean H | CV | min H | stop |
|---:|---:|---:|---:|---|
| 0.00 | 0.256358 | 0.576113 | 0.046114 | no transfer |
| 0.30 | 0.473936 | 0.055427 | 0.369874 | no transfer |
| 0.50 | 0.490834 | 0.046029 | 0.410031 | no transfer |
| 0.60 | 0.494923 | 0.043718 | 0.419748 | no transfer |
| **0.70** | **0.498579** | **0.037022** | **0.433779** | no transfer |
| **0.80** | **0.500223** | **0.035534** | **0.442186** | no transfer |
| 0.90 | 0.483617 | 0.031641 | 0.421198 | CV before an endogenous move |
| 1.20 | 0.495161 | 0.024129 | 0.452756 | CV before an endogenous move |

The high-preload cases demonstrate a stopping-confound: low dispersion induced by the initial schedule can itself satisfy the CV criterion.

### Warm-start decoupling

The second audit uses exact preliminary stock timing, tries destination years in ascending Harmony order, and forbids CV acceptance before at least one search pass.

| preload | mean H | CV | min H | accepted endogenous moves | stop |
|---:|---:|---:|---:|---:|---|
| 0.00 | 0.256618 | 0.576456 | 0.046148 | 24 | full failed pass |
| 0.30 | 0.454100 | 0.091099 | 0.344906 | 92 | full failed pass |
| 0.50 | 0.485749 | 0.047135 | 0.401027 | 62 | full failed pass |
| 0.70 | 0.493849 | 0.041846 | 0.421709 | 50 | full failed pass |
| 0.80 | 0.496491 | 0.039091 | 0.429610 | 41 | full failed pass |
| **0.90** | **0.498483** | 0.035252 | 0.439597 | 34 | full failed pass |
| 1.00 | 0.487982 | 0.028605 | 0.430618 | 1 | CV |
| 1.20 | 0.494748 | **0.025040** | **0.450413** | 1 | CV |

The spread remains large after the attempted decoupling: mean-Harmony range 0.328985, CV range 1.383842, worst-year-Harmony range 0.764971. The initializer is therefore not merely a speed parameter.

## C21: shadow continuation

The finite-horizon principle is source-supported: a published plan should be evaluated in a longer computational window so that near-terminal investment is not distorted by an artificial endpoint. For the Chapter 6 example, a good five-year plan with a fourteen-year industrial-capital horizon may be evaluated over nineteen years and years after five disregarded.

The **content of the fourteen shadow years is a separate question**. `csvplan.jl` repeats the last supplied targets and labour. That policy is useful and reproducible, but the currently available textual passage does not uniquely prescribe it.

Perturbing only shadow rows by ±10% changes published-period results. Therefore shadow continuation must be treated as an economic boundary assumption, not as a harmless file-padding operation.

Reconciled implementations must record the continuation policy in output provenance. A caller must be able to distinguish at least `repeat_last` from any future scenario-driven continuation.

## C23/C24: failed destinations

Under the text-supported global-lowest rule, the worst year should be tried first. A failed attempt at that year does not logically imply that every other year lacks a positive transfer. The ranked-fallback audit confirms this on the demonstration problem: after the worst year blocks, another destination admits one more positive move.

The difference is numerically small, so there is no basis for rewriting history. The correct split is:

- `historical`: first blocked destination terminates, exactly as `csvplan.jl`;
- `reconciled`: a full ordered pass can be used as a completion rule, but its provenance is `our_choice`.

The full-pass rule should not be described as a recovered step of the nine-step algorithm.

## C29 and C07: stopping and step size

The CV threshold, maximum iteration count, and epsilon are controls of the numerical procedure, not fixed economic propositions.

The audit shows that changing the CV threshold can terminate materially earlier. It also shows that a high preliminary investment can make CV small before the controller has done useful work. Therefore every reported result should include at least: threshold, maximum iterations, epsilon, accepted-move count, attempt count, and stop reason.

The text's epsilon expression remains useful as a named suggested calibration. It does not override the matrix value by authority because Cockshott explicitly labels it a first suggestion and his own executable witnesses use different operational scalings.

## Profiles to be used from now on

### Historical replay profile

This profile exists solely to reproduce `csvplan.jl` and remains implemented by `legacy.py`:

- preliminary replacement warm start: 0.70;
- historical preliminary stock propagation;
- repeat-last shadow targets/labour;
- active matrix destination/stop semantics;
- epsilon `0.25 / depreciation_horizon`;
- CV threshold 0.034;
- maximum iteration counter 3000;
- matrix prototype quirks preserved where required for numerical replay.

### Reconciled reconstruction profile

This profile is **not yet to be called a final canonical Cockshott implementation**. Its source-supported core is:

- correct vector accounting and all-product robust Harmony;
- candidate-state non-negativity checks;
- exact source-to-destination depreciation and stock recurrence;
- global-lowest destination as prescribed by Design/Chapter 6;
- positive overall-Harmony gain for accepted moves.

Residual controls must carry provenance:

- warm-start level/policy: explicit boundary-condition parameter, no authorial fixed default;
- shadow continuation: explicit policy, `repeat_last` only as a documented reproducibility option;
- failed-destination completion: full ordered pass allowed only as `our_choice`;
- epsilon: explicit parameter, with named historical and textual-suggestion presets;
- CV threshold and max iterations: explicit tunables;
- depreciation horizon: explicit planning-window parameter.

Until an endogenous initializer is developed and tested, a reconciled run using a nonzero warm start must say so in its output metadata. A run starting from zero should not be represented as equivalent to the historical matrix algorithm, because the audit shows that the current local search does not reliably bootstrap from that state.

## Remaining open technical item

The main unresolved algorithmic item relevant to the core controller is C26: how to translate a desired Harmony increase in the destination year into the multi-good additional-capital matrix. The historical prototype uses `current_stock * scale_increment`; an explicit `C * target_gross - current_stock` construction would be a reconstruction unless a primary source is found.

A second, separate engineering problem is endogenous initialization. Solving it could remove the arbitrary preload from the reconciled profile, but it must not be smuggled into the historical reconstruction. Any such method must be introduced as a new optimization subproblem, validated against the textual stock/accounting constraints, and evaluated for sensitivity before it can become a recommended default.
