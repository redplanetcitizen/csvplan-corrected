# csvplan staged composite audit results

## Scope

This audit adds source-supported changes in a controlled sequence. It does **not** define a canonical replacement for Paul Cockshott's historical `csvplan.jl`.

Throughout P0-P3 the following historically ambiguous choices remain fixed at the matrix-prototype values:

- preliminary replacement schedule `initialinvestmentlevel = 0.7`;
- matrix epsilon `0.25 / depreciationhorizon = 1/56` for a 14-year horizon;
- no-transfer termination semantics.

Only P4 changes epsilon, as an explicit optional tuning experiment.

The historical P0 run again reproduces the verified `legacy.py` oracle exactly. All 18 repository tests pass.

## Results

| Stage | Changes relative to previous stage | Mean H | CV | Worst-year H | Accepted moves | Stop |
|---|---|---:|---:|---:|---:|---|
| P0 | historical `csvplan.jl` | 0.483594243 | 0.048835808 | 0.402582327 | 331 | no transfer |
| P1 | fix C13 + C02 + C12 | 0.481993724 | 0.039850804 | 0.408119149 | 148 | no transfer |
| P2 | P1 + exact source/destination depreciation C11/C16 | 0.484719940 | 0.066689482 | 0.398113541 | 29 | no transfer |
| P3 | P2 + global-lowest destination C05 | **0.498578600** | **0.037022495** | **0.433778848** | 43 | no transfer |
| P4 | P3 + printed first-suggestion epsilon 1/15 | 0.495652050 | 0.051296981 | 0.434054751 | 12 | no transfer |

No stage generated a negative net-output cell.

## P1: confirmed indexing/constraint defects only

P1 combines only the three defects whose classification rests on local program semantics rather than on a choice between alternative controllers:

- C13: use the investment-by-commodity row vector when subtracting accumulation from final output;
- C02/C28: include the last actual product in the robust annual Harmony minimum;
- C12: test source-year non-negativity on the candidate scenario rather than on the pre-transfer scenario.

The initial Harmony changes immediately because C13 alters the accounting of the already-present 70% preliminary investment schedule. Final mean Harmony is slightly lower than the historical prototype, while CV and worst-year Harmony both improve. P1 and P0 are therefore non-dominating under the agreed three-metric rule.

This confirms why these changes must be justified by model and indexing semantics rather than by selecting the numerically best output ex post.

## P2: add internally consistent depreciation

P2 adds exact inverse gross-up from source to destination and exact forward survival for the endogenous correction transfer. The first accepted correction changes source year from zero-based 3 in P1 to zero-based 0 in P2.

Relative to P1:

- mean Harmony rises by `+0.002726216`;
- CV worsens by `+0.026838678`;
- worst-year Harmony falls by `-0.010005608`.

Thus exact depreciation accounting creates a substantial performance trade-off under the historical sequential controller. Again, numerical ranking cannot override the stock chronology: C11/C16 are model-consistency questions.

## P3: add the textual global-lowest destination rule

P3 makes one further change: instead of the active matrix-prototype sequential scan of below-mean years, it follows the Design/Chapter 6/scalar-code rule of selecting the current global minimum Harmony year.

This changes the first correction from zero-based destination year 9 to year 17 in the P2 state.

Relative to P2, P3 improves **all three** agreed performance measures:

- mean Harmony: `0.484719940 -> 0.498578600` (`+0.013858660`);
- CV: `0.066689482 -> 0.037022495` (`-0.029666987`);
- worst-year Harmony: `0.398113541 -> 0.433778848` (`+0.035665307`).

P3 also strictly dominates the historical P0 prototype itself:

- higher mean Harmony (`0.498579` vs `0.483594`);
- lower CV (`0.037022` vs `0.048836`);
- higher worst-year Harmony (`0.433779` vs `0.402582`).

This is the strongest result of the audit so far. It does **not** prove that P3 is the uniquely intended Cockshott implementation, because it still retains code-only or tunable historical choices such as the 70% preliminary schedule. It does show that once the direct accounting defects and the depreciation chronology are made internally consistent, the explicitly documented global-lowest rule repairs the poor dispersion introduced under the historical sequential controller and produces a result that strictly dominates the historical demonstration run on the agreed Harmony criteria.

P3 stops through `no_transfer`, not through the CV threshold. Its final CV `0.0370225` remains slightly above the historical threshold `0.034`.

## P4: printed epsilon suggestion on top of P3

P4 changes only epsilon from the historical matrix value `1/56` to the printed first suggestion `1/15`.

Relative to P3:

- mean Harmony falls by `-0.002926550`;
- CV worsens by `+0.014274486`;
- worst-year Harmony rises only slightly by `+0.000275903`.

Neither P3 nor P4 strictly dominates the other because P4 has the slightly higher minimum, but P3 is substantially better on mean Harmony and dispersion. This reverses the one-factor Stage B result, where `1/15` dominated the historical controller. The epsilon effect is therefore strongly interaction-dependent.

This supports keeping epsilon as a tuning parameter rather than elevating the printed “first suggestion” to a normative constant. The historical smaller epsilon remains a defensible value in the current P3 composite.

## What the composite audit resolves

The combined evidence now supports the following distinctions:

1. C13, C02/C28 and C12 are corrections of local indexing/object-selection defects, irrespective of whether their numerical effect is favourable.
2. C11/C16 should be made internally consistent with the stated stock chronology; numerical performance under the old sequential controller is not a valid reason to preserve an inconsistent time index.
3. C05 global-lowest has direct textual support, a scalar Julia witness, a dormant implementation in the matrix source, and now strict numerical dominance both as a one-factor change and inside the source-admissible composite.
4. C07 epsilon remains a genuine tuning choice. Its ranking reverses when other corrections are present.
5. C14 preliminary 70% remains unresolved as an authorial/theoretical matter. It is retained in P3 and is the next high-value interaction to isolate.

## Next checkpoint

The next experiment should hold P3 fixed and vary **only C14**, the preliminary replacement schedule. The purpose is not to find the best percentage by curve fitting. It is to determine whether the 70% schedule is:

- merely an initialization heuristic that changes convergence speed but not the attainable plan;
- a substantive prior allocation without which the text-supported controller cannot reach a comparable solution;
- or one point in a broad basin of preliminary schedules producing essentially the same result.

A sensitivity run at least at preliminary levels `0.0, 0.25, 0.50, 0.70, 1.00` should record the same three Harmony metrics, accepted moves, stop reason, and first divergence. Only after that test should C14 be adjudicated as retained implementation specialisation, optional initialization parameter, or unresolved code-only assumption.