# csvplan Stage B ambiguity audit results

## Scope

Stage B tests controller and code-only choices one factor at a time. Every run starts from the verified historical `csvplan.jl` / `legacy.py` behaviour and deliberately retains all Stage A behaviours, including the historical investment-subtraction, Harmony slicing, positivity test, and disabled inverse depreciation. The purpose is causal attribution, not construction of a combined alternative solver.

The baseline oracle check passed. All 18 repository tests also passed after the audit run.

Historical baseline:

- mean Harmony: `0.4835942427893382`
- sum Harmony: `9.188290612997426`
- CV: `0.04883580780685209`
- worst-year Harmony: `0.40258232651431725`
- accepted moves: `331`
- attempted corrections: `332`
- displayed iteration counter: `811`
- stop: `no_transfer`
- negative net-output cells: `0`

## Results

| Variant | First divergence | Mean H | Delta mean H | CV | Delta CV | Min H | Delta min H | Accepted | Stop |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline `csvplan.jl` | n/a | 0.483594243 | n/a | 0.048835808 | n/a | 0.402582327 | n/a | 331 | no transfer |
| B1 C14: preliminary 70% schedule OFF | initial Harmony | 0.243748382 | -0.239845861 | 0.606313364 | +0.557477556 | 0.041814529 | -0.360767798 | 53 | no transfer |
| B2 C05: global-lowest destination | first correction | 0.486871678 | +0.003277435 | 0.039509576 | -0.009326232 | 0.423877515 | +0.021295188 | 117 | no transfer |
| B3 C07: printed first-suggestion epsilon = 1/15 | first correction | 0.485050728 | +0.001456485 | 0.047869145 | -0.000966663 | 0.407269780 | +0.004687454 | 100 | no transfer |
| B4 C24: continue after failed destination | only after historical path would stop | 0.486798259 | +0.003204017 | 0.041187874 | -0.007647934 | 0.423902422 | +0.021320096 | 389 | no-transfer full pass |

No Stage B run produced a negative net-output cell on the demonstration dataset.

## B1 / C14: the 70% preliminary schedule is structurally important

Removing only `initialinvestmentlevel = 0.7` while retaining the historical controller does not produce a comparable alternative plan. Initial mean Harmony falls to `0.242097874`, and the controller stops after only 53 accepted transfers with final mean Harmony `0.243748382`, CV `0.606313364`, and worst-year Harmony `0.041814529`.

The historical prototype strictly dominates this isolated B1 variant on all three agreed numerical criteria.

This result does **not** prove that the 70% rule is a textual requirement. C14 remains `CODE-ONLY`. It shows instead that the historical controller is strongly dependent on its preliminary replacement schedule: simply deleting the code-only initialization while leaving the rest of `csvplan.jl` unchanged is not a viable reconstruction of the documented iterative procedure. Any no-preliminary variant must therefore be assessed together with the controller assumptions that make the nine-step textual procedure work from a depreciated-stock starting path.

## B2 / C05: global-lowest destination selection

The global-lowest variant changes the very first correction: the historical sequential scan first acts on zero-based year 9, whereas the global-minimum rule acts on zero-based year 18, the terminal computational year with the lowest initial Harmony.

Holding every other historical behaviour fixed, global-lowest **strictly dominates the historical sequential-below-mean scan** under the agreed metrics:

- mean Harmony rises by `0.003277435`;
- CV falls by `0.009326232`;
- worst-year Harmony rises by `0.021295188`.

The result is especially relevant because both the Design and Chapter 6 explicitly state “select the year with the lowest harmony”, and `harmony2.jl` implements a global minimum. The matrix prototype contains a global-minimum function but comments out its active call and instead scans below-mean years sequentially. On the currently available evidence, C05 should therefore be upgraded from a neutral textual variant to **DIRECT TEXT/CODE CONFLICT WITH NUMERICAL SUPPORT FOR THE TEXTUAL RULE**. The missing standalone `Using csvplan.jl` source could still qualify this adjudication if it explicitly documents the sequential scan as a deliberate matrix-specific revision.

## B3 / C07: epsilon

The historical matrix prototype uses

`epsilon = 0.25 / 14 = 1/56 ≈ 0.0178571`.

The textual formula is introduced only “as a first suggestion”. With a 14-year horizon it gives

`epsilon = 1/(1+14) = 1/15 ≈ 0.0666667`.

Holding everything else historical, the larger first-suggestion epsilon strictly dominates the matrix default on this dataset:

- mean Harmony rises by `0.001456485`;
- CV falls by `0.000966663`;
- worst-year Harmony rises by `0.004687454`;
- accepted moves fall from 331 to 100.

This is evidence that the printed suggestion is numerically effective here, but it is **not** evidence that `1/56` is a defect: Cockshott explicitly presents the formula as a suggestion intended to avoid oscillation, not as a mandatory invariant. C07 remains an implementation-parameter ambiguity unless another primary source fixes the matrix value normatively.

## B4 / C24: stopping at the first failed destination

The historical prototype stops the entire planning loop as soon as the currently scanned below-mean destination has no preceding source year producing a positive overall-Harmony gain. The alternative B4 continues testing the remaining below-mean years and stops only after a complete pass produces no accepted transfer.

The two trajectories are identical through all 332 historical correction attempts. The first divergence is therefore not a different earlier move but the decision to stop. Continuing the scan yields 389 accepted moves in total and strictly dominates the historical stop rule:

- mean Harmony rises by `0.003204017`;
- CV falls by `0.007647934`;
- worst-year Harmony rises by `0.021320096`.

The verified nine-step textual algorithm says that an attempted investment must not reduce overall Harmony, but the available Chapter 6/Design passages do not state that failure for one destination requires global termination. C24 should therefore be classified **CODE-ONLY STOPPING RULE, NUMERICALLY DOMINATED ON THE DEMONSTRATION DATASET**. This is not yet enough to call it a programming defect; the missing operational documentation may matter.

## Consequences for the audit

Stage B materially narrows the uncertainty.

1. **Do not remove the 70% initialization in isolation.** The matrix controller depends strongly on it. C14 remains undocumented rather than erroneous.
2. **Global-lowest is now the strongest candidate for a source-preferred destination rule.** It has explicit textual support, a scalar-code witness, a dormant function in `csvplan.jl`, and strict numerical dominance over the active sequential scan on the demonstration dataset.
3. **The printed epsilon suggestion performs better than the matrix default here, but remains a tunable implementation choice.**
4. **The historical first-failure global stop is numerically costly and not found in the currently available nine-step text.** It remains code-only pending recovery of operational documentation.

The next isolated tests should resolve the depreciation timing questions C11b/C16 and revisit C16 with the preliminary 70% schedule disabled so that the timing effect is not conflated with the code-only initialization.