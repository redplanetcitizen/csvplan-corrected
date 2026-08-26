# csvplan Stage A one-factor audit results

## Scope

These tests begin from the verified Python replay of Paul Cockshott's historical `csvplan.jl` matrix prototype. Each run changes one local behaviour only. The historical prototype itself is not modified.

The Stage A harness first verifies that all switches off reproduce the packaged `legacy.py` oracle. That check passed.

Baseline (`csvplan.jl` / `legacy.py`):

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

| Variant | First divergence | Mean H | Delta mean H | CV | Delta CV | Min H | Delta min H | Accepted moves | Stop |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline `csvplan.jl` | n/a | 0.483594243 | n/a | 0.048835808 | n/a | 0.402582327 | n/a | 331 | no transfer |
| A1 C13: subtract investment as commodity row vector | initial Harmony | 0.481993724 | -0.001600519 | 0.039850804 | -0.008985004 | 0.408119149 | +0.005536822 | 148 | no transfer |
| A2 C02: include last actual product in annual minimum | none | 0.483594243 | 0 | 0.048835808 | ~0 | 0.402582327 | 0 | 331 | no transfer |
| A3 C12: test positivity on candidate scenario | none | 0.483594243 | 0 | 0.048835808 | 0 | 0.402582327 | 0 | 331 | no transfer |
| A4 C11a: enable matrix prototype's existing inverse-depreciation path | first accepted move | 0.496598556 | +0.013004313 | 0.049012226 | +0.000176418 | 0.410799994 | +0.008217667 | 114 | no transfer |
| A5 C16: exact forward investment-stock survival timing | initial Harmony | 0.463302364 | -0.020291878 | 0.051448921 | +0.002613113 | 0.383772658 | -0.018809669 | 599 | no transfer |

All runs ended with zero negative net-output cells on this dataset.

## Interpretation by row

### A1 / C13: commodity-vector investment subtraction

This change is economically and dimensionally substantial. The historical Julia expression uses one-index access on a matrix and therefore subtracts a scalar, broadcast across the product vector. Replacing it with the investment-by-commodity row changes the initial Harmony immediately because the preliminary investment schedule is already present before the iterative controller starts.

Numerically the variant is **not dominated by the historical prototype**: it has lower mean Harmony but materially lower CV and a higher worst-year Harmony. Therefore performance alone cannot adjudicate the issue. The source/vector semantics remain decisive.

### A2 / C02: last product in robust annual Harmony

On the current EU dataset the correction is numerically inert: there is no first divergence, and all final metrics and moves match the prototype. The last product is never the binding minimum along the historical trajectory.

This is useful evidence: the suspected slicing defect can be discussed independently of the published numerical example because fixing it does not change this dataset's result.

### A3 / C12: post-candidate non-negativity

On the current EU dataset the post-candidate test is also numerically inert. Every source candidate that matters to the historical path passes the same positivity classification under the pre- and post-transfer checks.

This does **not** make the two rules equivalent in general. It establishes only that the historical demonstration dataset does not exercise the difference.

### A4 / C11a: inverse depreciation enabled

Enabling the inverse-depreciation mechanism already present in the matrix source changes the very first accepted move while preserving the same source and destination year. Mean Harmony rises from `0.483594243` to `0.496598556` and worst-year Harmony rises from `0.402582327` to `0.410799994`; CV worsens slightly from `0.048835808` to `0.049012226`.

Thus A4 is not a strict Pareto improvement under the agreed three metrics because CV is marginally worse. It nevertheless produces the largest positive change in mean and minimum Harmony among Stage A variants. This run tests only activation of the matrix prototype's latent inverse-depreciation call. It does **not** correct the separate timing issue described in `CSVPLAN_DEPRECIATION_TIMING_ADDENDUM.md`.

### A5 / C16: forward depreciation timing

Using direct survival timing `I*(1-d)^p` lowers mean Harmony, raises CV and lowers the worst-year Harmony on this dataset. Under the numerical dominance rule, the historical prototype dominates this isolated A5 variant.

This numerical result does not by itself validate the historical timing, because the textual stock recurrence is a hard model statement. In addition, A5 changes the propagation of the code-only 70% preliminary investment schedule from the initial state onward, which explains why divergence occurs before the iterative controller begins. The timing question therefore requires a second test after the preliminary-schedule ambiguity has been isolated.

## Stage A adjudication status

Stage A does not yet authorize a combined corrected solver.

- C02: source-level defect remains plausible; no effect on current demonstration data.
- C12: source-level defect remains plausible; no effect on current demonstration data.
- C13: strong dimensional/source conflict; numerically creates a trade-off rather than a dominance result.
- C11a: direct text/code conflict; large numerical effect; timing subproblem still open.
- C16: timing conflict identified; numerical result is confounded by propagation of the preliminary 70% schedule and must be revisited after C14.

The next audit stage should isolate controller/code-only choices, beginning with C14 (70% preliminary schedule), C05 (global-lowest versus sequential below-mean destination selection), C07 (epsilon), and C24 (stop at first failed destination versus continuing the scan).
