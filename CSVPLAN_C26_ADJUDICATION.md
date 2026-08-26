# C26 adjudication: multi-good additional-capital update

## Question

The matrix prototype converts a proposed improvement in the destination-year plan-fulfilment ratio into an additional-capital matrix by scaling the destination stock:

`additional_capital = current_stock * scale_increment`.

The verified Design/Chapter 6 material states the economic requirement that investment be moved from preceding years so as to improve the low-Harmony destination, but it does not print a unique multi-good matrix formula for the amount of capital required. C26 therefore cannot be decided by textual quotation alone.

## Audit design

The C26 audit holds the cumulative P3 state fixed:

- confirmed vector/indexing/constraint corrections;
- exact endogenous source-to-destination depreciation and stock timing;
- global-lowest destination;
- historical 70% preliminary schedule, solely to hold initialization constant during this test;
- historical matrix epsilon;
- historical first-blocked stopping rule.

Only the destination additional-capital construction changes.

Three rules were tested:

1. **historical stock-proportional**: `max(S_dest * scale, 0)`;
2. **coefficient increment**: map the proposed final-demand increment `g_t * scale` through Leontief gross output and then through `C`, without crediting existing stock slack;
3. **required-stock gap**: compute a proposed destination plan-ray level, add already scheduled investment to final demand, map through Leontief and `C`, then subtract existing destination stock and keep only positive gaps.

Rules 2 and 3 are reconstruction experiments. They are not attributed to Cockshott.

The historical rule was required to reproduce the P3 oracle exactly. It did.

## Results

| C26 rule | mean H | CV | min H | accepted moves | stop |
|---|---:|---:|---:|---:|---|
| historical stock-proportional | 0.498578600 | 0.037022495 | 0.433778848 | 43 | no transfer |
| coefficient increment | 0.502157617 | 0.038475276 | 0.436141212 | 37 | no transfer |
| required-stock gap | 0.337716070 | 0.328955630 | 0.172411440 | 0 | no transfer |

Both reconstruction rules diverge on the first attempted correction. The coefficient-increment construction raises mean and minimum Harmony relative to the historical rule but worsens CV. It therefore does not strictly dominate P3 on the agreed three metrics. The required-stock-gap construction admits no positive source on the first destination under this controller and effectively leaves the initial state unchanged.

All three runs preserve nonnegative net outputs. The C26 workflow reproduced the P3 oracle and the repository's 18-test suite passed.

## Decision

**C26 source status remains INDETERMINATE, but the implementation decision is closed for the reference reconstruction.**

The historical stock-proportional rule is retained as the **matrix-prototype implementation specialization** because:

1. it is the only directly witnessed executable multi-good rule in the source bundle;
2. no verified primary text supplies a different unique matrix formula;
3. the alternative coefficient construction is a genuine reconstruction and does not strictly dominate the historical rule on mean Harmony, CV, and worst-year Harmony simultaneously;
4. the naïve required-stock-gap construction is incompatible with the present local-search controller on the demonstration problem.

This retention does **not** convert `current_stock * scale_increment` into a theoretical New Harmony invariant. Every reconciled result must identify the rule as `historical_matrix_specialization` in provenance.

## Consequences

For the reference reconciled solver:

- use the historical stock-proportional C26 update;
- apply the already-adjudicated corrections around it: vector accounting, all-product robust Harmony, candidate-state positivity, exact depreciation timing, and global-lowest destination;
- do not describe the C26 formula as printed in Design/Chapter 6;
- allow alternative C26 rules only as explicitly experimental profiles with separate regression results.

The coefficient-increment variant may be retained as an experimental branch for later economic analysis, because it improves mean and worst-year Harmony on this dataset. It must not silently replace the matrix witness.

## Remaining initialization issue

C26 no longer blocks construction of a reference reconciled solver. The separate initialization problem remains: the historical 70% preload is a code-only structural warm start/boundary condition, and the current local search is materially path-dependent on it. This does not prevent a reproducible reference profile if the preload is explicitly named and provenance-labelled. It does prevent claiming that 70% is a source-derived theoretical default.
