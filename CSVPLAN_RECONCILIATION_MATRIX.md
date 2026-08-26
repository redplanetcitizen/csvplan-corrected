# csvplan source-code reconciliation matrix

## Status

This document is an **audit instrument, not a specification**. It suspends any presumption that a reconstruction differing from Paul Cockshott's `csvplan.jl` is automatically more faithful to his intended algorithm.

No algorithmic behaviour is to be changed on the basis of this matrix until the relevant row has been adjudicated. `csvplan.jl` remains the immutable historical prototype sample; `legacy.py` remains its verified Python replay.

The audit compares four kinds of evidence:

1. `Design for Julia implementation of the New Harmony algorithm` (Paul Cockshott, undated in the available copy).
2. Chapter 6, `Theory of Optimal Planning`, current project copy.
3. Cockshott's scalar Julia example `harmony2.jl`, explicitly identified by the Design as the code used for the scalar results.
4. Cockshott's matrix Julia prototype `csvplan.jl`.

### Source gap

A standalone primary file entitled `Using csvplan.jl` is **not present in the currently searchable/uploaded source bundle used for this audit**. Earlier project discussion referred to such operational documentation, but its remembered contents are not treated here as primary evidence. Rows whose classification could change if that document is recovered are marked `SOURCE GAP`.

## Classification vocabulary

- **CONCORDANCE**: text and code implement the same rule.
- **IMPLEMENTATION SPECIALISATION**: code chooses a concrete method compatible with a more general textual rule.
- **TEXTUAL VARIANT**: Cockshott's own textual/code witnesses implement materially different variants, with no present basis for calling one erroneous.
- **CODE-ONLY**: behaviour appears in `csvplan.jl` but is not found in the available textual algorithm statement.
- **TEXT-ONLY**: explicit textual prescription is absent from the matrix prototype.
- **DIRECT CONFLICT**: code and text prescribe incompatible behaviour for the same operation.
- **PROBABLE IMPLEMENTATION DEFECT**: direct conflict plus a strong local programming indication that the behaviour is accidental.
- **INDETERMINATE**: evidence is insufficient to adjudicate.
- **OUR CHOICE**: behaviour introduced by the Python reconstruction and not attributable to Cockshott.

A behaviour is **not** classified as a defect merely because it is undocumented.

## Reconciliation matrix

| ID | Decision / invariant | Textual evidence | `harmony2.jl` scalar witness | `csvplan.jl` matrix prototype | Preliminary classification | Required test / action |
|---|---|---|---|---|---|---|
| C01 | Fractional Harmony | Design eq. (6) and Chapter 6 eq. (6.8): `H(x)=x/(1.1+x)` | lines 3-12 implement the same function and inverse | lines 385-401 implement the same function and inverse | **CONCORDANCE** | Regression only |
| C02 | Robust annual Harmony is the worst per-product Harmony | Design states that the alternative to the projection metric is the lowest per-product Harmony; Chapter 6 eqs. (6.10)-(6.11) repeats this and maximises its sum over years | Scalar model has one product, so no cross-product test | lines 444-451 compute product Harmonies but then apply `[1:end-1]` after labour has already been removed | **PROBABLE IMPLEMENTATION DEFECT** | A/B: exact Julia slicing vs all products; record first divergent move and final metrics |
| C03 | Overall intertemporal objective | Design eqs. (7)/(9) and Chapter 6 eqs. (6.9)/(6.11) use the sum of annual Harmony; Step 8 says no investment should reduce overall Harmony across time | lines 232-248 select source year by source loss + destination gain | lines 550-555 evaluate a candidate by change in **mean** Harmony; with fixed horizon this ranks candidates exactly as sum Harmony | **CONCORDANCE** | Verify fixed-horizon equivalence numerically |
| C04 | Mean, standard deviation and coefficient-of-variation stopping criterion | Design steps 4-5; Chapter 6 steps 4-5 | lines 147-174 | lines 457-471 and 821-834 | **CONCORDANCE** on rule; threshold is parameter-specific | Keep threshold as parameter; do not infer universal value |
| C05 | Destination year: global lowest Harmony | Design step 6 and Chapter 6 step 6 explicitly say select the year with the lowest Harmony | lines 178-193 implement global minimum | function at lines 496-510 implements global minimum, but active loop lines 818-857 scans sequentially and acts on each `h[i] < meanh`; global-minimum call is commented out at line 843 | **DIRECT CONFLICT / TEXTUAL VARIANT**; `SOURCE GAP` may matter | A/B global-lowest vs sequential-below-mean, with all other behaviour held Julia-identical |
| C06 | Move destination toward current mean Harmony | Design step 7; Chapter 6 step 7 | lines 199-209 invert Harmony and target the mean | lines 632-650 invert mean/current Harmony and calculate the gap | **CONCORDANCE** in principle | Regression and formula audit |
| C07 | Size of each move, epsilon | Design/Chapter 6: choose epsilon small enough to avoid oscillation; `1/(1+1/Delta)` is explicitly only "a first suggestion" | line 45 sets `3/14`; lines 228-262 introduce additional scaling, so scalar code does not literally instantiate the printed suggestion | line 15 sets `0.25/depreciationhorizon`, hence 1/56 at horizon 14 | **TEXTUAL VARIANT / IMPLEMENTATION SPECIALISATION** | A/B printed suggestion vs Julia fixed epsilon; do not label either error solely by formula mismatch |
| C08 | Source years must precede destination | Design/Chapter 6 step 8: at least one previous year | lines 233-249 consider `1:year-1` | lines 584-603 consider `1:destyear-1` | **CONCORDANCE** | Regression only |
| C09 | Choose source year by best overall Harmony effect | Step 8 gives the overriding no-reduction principle but does not uniquely specify a source-search rule | scalar code selects the previous year maximizing destination gain plus source loss | matrix code constructs complete candidate scenarios and selects the source with greatest positive mean-Harmony gain | **IMPLEMENTATION SPECIALISATION**, strongly supported by scalar witness | Keep as candidate operational rule; quantify against alternatives only if needed |
| C10 | No accepted investment may lower overall Harmony | Explicit in Design/Chapter 6 comment on Step 8 | scalar code chooses best gain but initializes `bestgain` negative and does not explicitly reject a still-negative best source | matrix code initializes `bestgain=0`; if no positive source exists it terminates | **CONCORDANCE** for matrix prototype; scalar witness weaker | Regression: accepted move must have positive delta mean/sum Harmony |
| C11 | Depreciation between source and destination | Design/Chapter 6 explicitly says capital built earlier reaches destination depreciated; equation/example gives `(1-d)^(t-1)` style survival | lines 47-57 and 243-256 explicitly inverse-depreciate source investment | lines 156-163 define inverse depreciation, but global `inversedepreciateinvestments=false` at line 12 disables it in the active source search at lines 590-594 | **DIRECT CONFLICT**, with strong evidence from scalar Cockshott code | A/B flag on/off; this is a high-priority adjudication row |
| C12 | Candidate investment must not create negative net products in source year | Explicit in Design and Chapter 6 comment on Step 8 | scalar code does not implement a vector non-negativity test because it is single-good | matrix lines 595-602 test `s.netoutputs[y]`, i.e. the **pre-transfer** scenario, not `newscenario` | **PROBABLE IMPLEMENTATION DEFECT** | A/B pre-check vs candidate post-check; reject candidate if any post-transfer net product < 0 |
| C13 | Net final output must subtract investment by commodity | Design eq. (5): final consumption = output minus accumulation minus productive consumption; Chapter 6 uses final demand/net output vectors | scalar code subtracts scalar investment from scalar output | matrix line 428 uses `investmentsbytype[i]` on a 2-D matrix; Julia linear indexing therefore returns a scalar and broadcasts it across the whole product vector | **PROBABLE IMPLEMENTATION DEFECT** | Highest-priority accounting A/B: scalar-broadcast subtraction vs row-vector subtraction |
| C14 | Preliminary investment schedule at 70% of replacement | Nine-step Design/Chapter 6 procedure begins from depreciated initial stocks and does not state a uniform preliminary 70% replacement schedule | no corresponding 70% rule | line 14 sets `initialinvestmentlevel=0.7`; lines 773-787 assign `0.7*(caps .* dep)` in every non-terminal computational year before iteration begins | **CODE-ONLY** | A/B 70% on/off only after C13/C02/C12 accounting defects are isolated; absence from text alone is not evidence of error |
| C15 | Initial stock path before endogenous investment | Design/Chapter 6 step 2: assign each year's stock from starting stock depreciated appropriately | lines 103-115 use straight-line depreciation in scalar example | lines 372-381 use exponential depreciation; Design section 6 explicitly notes that `csvplan.jl` uses exponential depreciation unlike scalar example | **CONCORDANCE** with documented matrix specialisation | Regression only |
| C16 | Stock recurrence after investment | Design eq. (3), Chapter 6 dynamic stock equation: next stock = surviving stock + prior-year accumulation | scalar lines 219-226 propagate investment forward with depreciation | matrix lines 511-527 and 530-535 propagate investment into subsequent stocks | **CONCORDANCE** structurally | Direct recurrence test, including cell-specific depreciation |
| C17 | Within-period Leontief inversion | Design full-matrix section and Chapter 6 eq. (6.4): gross output `o=(I-A)^-1 f` | not used in scalar example | lines 175-181; update at lines 411-425 includes investment in final demand and derives gross output by inverse | **CONCORDANCE** | Regression / accounting identity |
| C18 | Capital and labour determine feasible scale | Design full-matrix discussion and Chapter 6 extension to multiple goods: compare required capital cells against stock, then labour | scalar output is `min(capital productivity, labour productivity)` | lines 182-217 compute cellwise capital ratios and labour constraint and take the minimum | **CONCORDANCE** | Constraint audit |
| C19 | Full-employment/replacement treatment in terminal computational year | Design/Chapter 6 step 1 sets final-year net target so gross output uses workforce and replacement covers depreciation | lines 90-98 implement scalar formula | lines 279-295 and 739-759 construct modified final target; because the input horizon is first extended, this applies to the last **computational** year | **IMPLEMENTATION SPECIALISATION**, consistent with extended-horizon interpretation | A/B only if exact terminal formula materially affects results |
| C20 | Computational horizon extends beyond published plan | Chapter 6 finite-horizon discussion: a five-year plan with a 14-year industrial-capital horizon may be optimised over 19 years and years after 5 disregarded | scalar example fixed at 5, no extension | lines 78-101 append `depreciationhorizon` rows; lines 865-879 display only original years | **CONCORDANCE** for the 5+14 example; universality of fixed 14 remains implementation-specific | Regression T -> T+14; separate question whether 14 should be fixed or data-dependent |
| C21 | Continuation targets and labour | Chapter 6 gives the 5->19 recommendation but does not, in the passage currently verified, uniquely specify how every shadow target/labour row must be generated | no extension | targets repeat last explicit row at lines 96-101; labour repeats last row at lines 78-86 | **CODE-ONLY / IMPLEMENTATION SPECIALISATION** | Keep as historical behaviour; search recovered operational documentation before declaring normative |
| C22 | Depreciation horizon = 14 | Chapter 6 says 14 years is an illustrative/common accounting horizon for machinery and uses 5+14=19 as an example; capital depreciation table itself is cell-specific | scalar line 44 = 14 | matrix line 13 = 14, comment says "hopefully this is a long enough estimate" | **IMPLEMENTATION SPECIALISATION**, not universal theoretical constant | Parameter sensitivity; do not replace cell-specific rates with 1/14 |
| C23 | Stop when no positive source transfer exists | Step 8 requires no reduction in overall Harmony but nine-step text does not state an explicit no-transfer terminal rule | scalar always chooses some best source, even if its best combined gain could be negative | matrix lines 604-610 terminate when no source gives gain > 0 | **IMPLEMENTATION SPECIALISATION / CODE-ONLY**; `SOURCE GAP` may matter | Preserve as prototype behaviour; test whether it prematurely stops before other destination years could improve |
| C24 | Stop at the first below-mean destination with no feasible positive transfer | Not specified in Design/Chapter 6 | n/a | active sequential scan terminates globally as soon as `Attempt_to_scale_up` fails for the current destination | **CODE-ONLY / INDETERMINATE** | A/B global stop vs continue scanning remaining below-mean destinations |
| C25 | Source-year cost valuation | Design discusses direct Leontief re-evaluation as possible but computationally expensive, then says labour values will be used as valuation vector for lower cost | scalar computes source-year Harmony loss directly in scalar units | matrix computes labour values `V` but `Attempt_to_scale_up` leaves `V` unused; instead it creates a full candidate scenario and recomputes mean Harmony | **TEXTUAL VARIANT / IMPLEMENTATION SPECIALISATION**: code uses a more direct, more expensive evaluation mentioned by the text | A/B only if reconstructing the valuation approximation itself; do not call current code erroneous |
| C26 | Additional capital required at destination | Text requires enough additional capital to raise destination production toward mean Harmony, with cell-specific `C` constraints; no unique matrix update formula is printed in the verified passages | scalar uses current stock times attempted scale increment | matrix lines 565-578 use current destination stock `csy * scaleincrement`, clipped at zero | **INDETERMINATE / IMPLEMENTATION SPECIALISATION** | Compare Julia formula with explicit `C*target gross - current stock` formula; label latter as reconstruction unless source found |
| C27 | Fixed technology matrix during plan | Design says assume no technology change for a relatively short interval; Chapter 6 says fixed A for simplicity and notes time-indexed A is a straightforward extension | n/a | one fixed A is used for all years | **CONCORDANCE** | None |
| C28 | Annual Harmony objective includes labour? | Text defines Harmony over final products; labour is a resource constraint, not a final-output target | scalar has no labour target in Harmony vector | matrix correctly removes labour from `g` before product ratios, but then erroneously removes one additional product at line 451 | **CONCORDANCE** on excluding labour; **PROBABLE DEFECT** only in the extra product slice | Covered by C02 |
| C29 | Threshold and maximum iteration constants | Text says "some threshold" and gives no universal matrix values in the verified algorithm statement | `mincoeff=0.01`, `maxiter=500` | `mincoeff=0.034`, `maxiter=3000` | **CODE-ONLY PARAMETERISATION** | Treat as tunable parameters, not theoretical constants |
| C30 | Reported plan vs optimisation window | Chapter 6 explicitly recommends disregarding years after year 5 in a 19-year optimisation window for a five-year plan | scalar reports all 5 | matrix reports only `TheLastYear-depreciationhorizon` years | **CONCORDANCE** | Regression only |

## Findings that are already strong enough to guide test ordering

The matrix does **not** yet adjudicate the ambiguous controller choices, but four rows have unusually strong evidence of local implementation defects because the program behaviour contradicts an explicit vector/constraint statement and the source code itself contains a programming-level indication of accident:

1. **C13: scalar broadcast subtraction of investment from a product vector.** The intended object is investment by commodity; `investmentsbytype[i]` is Julia linear indexing on a matrix.
2. **C02/C28: the last actual product is dropped from Harmony.** The adjacent source comment says the slice is to ignore labour, but labour has already been removed before the slice.
3. **C12: positivity is tested on the old scenario rather than the candidate scenario.** The text speaks about what the proposed investment "would result in".
4. **C11: inverse depreciation is explicitly described in both text and scalar code, is implemented as a function in `csvplan.jl`, but disabled by the global default flag.** This is a direct conflict; whether it is an intentional experimental switch or an unfinished default remains to be determined.

By contrast, **C14 (`initialinvestmentlevel=0.7`) is not currently a bug finding**. It is code-only. It must be tested, not deleted by presumption.

## Test sequence

To avoid interaction bias, tests should be executed in this order.

### Stage A: accounting / constraint defects

Start from the exact `legacy.py` replay of `csvplan.jl`. Change **one item at a time**:

- A1: C13 row-vector investment subtraction instead of scalar broadcast.
- A2: C02 include the last actual product in annual Harmony.
- A3: C12 post-candidate positivity check instead of pre-candidate check.
- A4: C11 inverse depreciation enabled.

For every A-test record the first iteration where the path diverges from the prototype and the final economic metrics.

### Stage B: code-only and controller ambiguities

Only after Stage A effects are known:

- B1: C14 preliminary 70% investment on/off.
- B2: C05 global-lowest destination vs sequential below-mean scan.
- B3: C07 Julia epsilon vs the printed first-suggestion epsilon.
- B4: C24 stop at first failed destination vs continue scanning other below-mean destinations.
- B5: C26 Julia stock-scaling capital request vs explicit capital-shortfall request.
- B6: C19 exact Julia terminal target vs alternative text-derived formalisation.
- B7: C25 direct scenario re-evaluation vs labour-value source-cost approximation, only if the latter can be implemented unambiguously from the text.

### Stage C: interactions

Test combinations only after the marginal effect of each Stage A/B item is known. The first combined run should contain only the Stage A changes supported by direct textual conflict. Ambiguous Stage B choices remain switches until independently adjudicated.

## Metrics and decision rule

Every run uses the same input tables and computational horizon and records:

- mean Harmony `mean(H_t)`;
- total Harmony `sum(H_t)`;
- Harmony coefficient of variation `std(H_t)/abs(mean(H_t))`;
- worst-year Harmony `min(H_t)`;
- accepted move count and attempted move count;
- stop reason;
- annual fulfilment ratios;
- annual investment totals and investment tensor;
- capital-stock path;
- any negative net output, flow-balance, labour or capital violation;
- first iteration at which the candidate path diverges from the historical prototype.

On a fixed horizon, maximising mean Harmony and maximising total Harmony are equivalent rankings. Numerical preference is assessed only **after** textual/physical admissibility.

If two source-compatible variants A and B satisfy all hard constraints, A dominates B only if:

`meanH_A >= meanH_B`, `CV_A <= CV_B`, and `minH_A >= minH_B`,

with at least one strict inequality. If one variant raises mean Harmony but worsens CV or worst-year Harmony, numerical performance alone does not adjudicate the textual ambiguity.

## Current adjudication boundary

At this stage:

- `csvplan.jl` is the historical prototype sample and is not to be edited.
- `legacy.py` is the validated numerical oracle for that prototype.
- no alternative controller is entitled to the label "more faithful" until the rows above are adjudicated;
- the existing `faithful.py` branch implementation is therefore an **experimental reconstruction under audit**, not a normative Cockshott implementation.

The next executable task is Stage A1, with the exact prototype held fixed as the baseline.