# csvplan adjudication status

## Purpose

This file consolidates the audit after the source/code matrix, Stage A, Stage B, and the isolated depreciation-timing tests. It supersedes the preliminary labels in `CSVPLAN_RECONCILIATION_MATRIX.md` where the two differ.

The historical reference remains Paul Cockshott's original `csvplan.jl`. `legacy.py` is its verified numerical replay. No combined alternative is yet canonical.

## 1. Programming defects now supported by both semantics and local code structure

### C13: investment subtraction uses scalar linear indexing

`investmentsByTypeandYear` explicitly returns a matrix `[year, sourceindustry]`. In `update_outputs`, the same matrix is added to the target row correctly as a vector, but net output is then computed with:

`finaloutput[i] .- investmentsbytype[i]`

On a Julia matrix, one-index access is linear indexing, so `investmentsbytype[i]` is a scalar, not the year-`i` commodity vector. Broadcasting subtracts that scalar from every product in `finaloutput[i]`.

The model statement is vector-valued final output: output less accumulation and productive consumption. The source-year example likewise says allocating one van to accumulation lowers current final van consumption by one, not every product by the same scalar.

**Status: CONFIRMED INDEXING DEFECT.**

Stage A1 shows that fixing it has a large numerical effect but creates a performance trade-off: lower mean Harmony, lower CV, and higher worst-year Harmony. Numerical performance is therefore not the reason for the correction; dimensional and model consistency are.

### C02/C28: an actual product is dropped from robust annual Harmony

`update_outputs` and the fulfilment-ratio calculation have already removed the labour column by using `1:end-1`. `harmonyarrayofarrays[i]` therefore contains product Harmonies only. The subsequent slice

`harmonyarrayofarrays[i][1:end-1]`

removes one additional element, despite the adjacent comment saying it is done to ignore labour.

**Status: CONFIRMED INDEXING DEFECT.**

On the EU demonstration data the omitted last product never becomes the binding minimum, so Stage A2 is numerically identical to the historical run. This makes the correction especially safe to identify: source semantics change, published demo results do not.

### C12: positivity is tested on the pre-transfer scenario

The text says a proposed investment must not be allowed if it **would result in** negative net products in the source year. The matrix prototype constructs `newscenario` and computes its gain, but tests positivity on `s.netoutputs[y]`, the old scenario.

**Status: CONFIRMED WRONG-OBJECT CHECK.**

Stage A3 is numerically inert on the EU demonstration dataset, so the historical example does not exercise the defect.

## 2. Direct text/code conflicts that are not automatically programming defects

### C05: destination-year rule

Design, Chapter 6, and scalar `harmony2.jl` all use the year with the lowest Harmony. `csvplan.jl` contains a function implementing that rule, but its active call is commented out and the live controller instead scans years sequentially, correcting each year whose Harmony is below the current mean.

**Status: DIRECT TEXT/CODE CONFLICT.**

Stage B2 gives additional evidence: global-lowest strictly dominates the active matrix scan on mean Harmony, CV, and worst-year Harmony. This strengthens the case for the textual rule but does not turn performance into authorship evidence.

A standalone operational source previously referred to as `Using csvplan.jl` is not present in the current searchable/uploaded audit bundle. If recovered, it may show that the sequential matrix scan was a deliberate later operational revision. Until then the conflict remains open at the historical-intent level.

### C11a: source-to-destination depreciation compensation disabled

The text explicitly requires earlier investment to arrive at the destination as depreciated capital. Scalar `harmony2.jl` inverse-depreciates the source investment. Matrix `csvplan.jl` contains an inverse-depreciation function but sets `inversedepreciateinvestments=false`.

**Status: DIRECT TEXT/CODE CONFLICT.**

Stage A4 / D1 show a large numerical effect when the dormant matrix path is enabled. The default-off flag could represent an unfinished or experimental switch, so the audit distinguishes conflict from accidental coding error.

### C11b/C16: depreciation timing

The stated stock recurrence makes investment produced in year `t` available in `t+1`; later stock dates should then contain the surviving amount after the corresponding number of full depreciation periods. The matrix recursive helper leaves amounts unchanged for an extra period relative to that chronology. Its latent inverse-depreciation call has the analogous off-by-one issue.

**Status: TIME-INDEXING CONFLICT; HIGH-CONFIDENCE IMPLEMENTATION DEFECT, but kept separate from C11a.**

The isolated depreciation audit shows that correcting timing does not improve all Harmony statistics. The justification is the temporal accounting identity, not ex post performance.

## 3. Code-only choices that must not be called defects without more evidence

### C14: preliminary 70% replacement schedule

`initialinvestmentlevel=0.7` preassigns 70% of `caps .* dep` in every nonterminal computational year before the iterative controller starts. The currently available nine-step textual procedure does not state this initialization.

**Status: CODE-ONLY INITIALISATION, NOT A BUG FINDING.**

Stage B1 shows that simply removing it while leaving the historical controller unchanged is catastrophic on the demonstration problem: mean Harmony falls to about 0.244, CV rises above 0.60, and worst-year Harmony falls to about 0.042. This shows that the historical controller relies heavily on the initialization. It does not show that 70% is theoretically required.

### C24: terminate after the first failed below-mean destination

The active matrix loop stops the whole search when the current destination has no source year with positive overall-Harmony gain. The verified nine-step text does not state this global stopping rule.

**Status: CODE-ONLY STOPPING RULE.**

Stage B4 continues scanning other below-mean destinations and strictly dominates the historical stop rule on all three agreed performance measures. Because the text does not explicitly prescribe the alternative either, the result is evidence about performance, not proof of authorial intent.

### C07: epsilon value

Matrix `csvplan.jl` uses `0.25/depreciationhorizon = 1/56` for horizon 14. The text gives `1/(1+1/Delta)`, equivalent to `1/15` for a 14-year depreciation horizon, only **as a first suggestion** to avoid oscillation. Scalar `harmony2.jl` uses yet another operational scaling.

**Status: TUNING / TEXTUAL VARIANT, NOT A DEFECT.**

Stage B3 shows that the printed first-suggestion value strictly dominates the matrix default on the EU demonstration run, but that does not convert a suggested tuning rule into a mandatory invariant.

## 4. Choices that currently look like legitimate implementation specialisations

- fixed 14-year computational extension for the demonstration, with reporting restricted to the original plan horizon;
- Leontief inversion within each year;
- cell-specific capital constraints followed by labour constraint;
- search over all preceding source years and selection of the source with greatest positive total/mean-Harmony gain;
- direct candidate-scenario re-evaluation of source cost instead of the cheaper labour-value approximation discussed in the Design;
- fixed `A` over the plan horizon in the demonstration.

These may be parameterised in a general implementation without being described as corrections to Cockshott.

## 5. Source gap clarified

The public SourceForge project contains a 223-byte `readme.txt`. That readme merely states that the theoretical description is in `newharmony.pdf`, announces a future video, and points to Cockshott's YouTube channel. It is **not** the detailed operational document previously referred to in project discussion as `Using csvplan.jl`.

Therefore no remembered statement from that missing operational document is currently used to override a conflict found in the primary code, Design, Chapter 6, or scalar Julia witness.

## 6. Current performance evidence

Historical baseline:

- mean H `0.483594243`
- CV `0.048835808`
- min H `0.402582327`

Strictly dominant one-factor variants found so far:

- C05 global-lowest: mean `0.486871678`, CV `0.039509576`, min `0.423877515`;
- C07 first-suggestion epsilon: mean `0.485050728`, CV `0.047869145`, min `0.407269780`;
- C24 continue after failed destination: mean `0.486798259`, CV `0.041187874`, min `0.423902422`.

These three performance findings have different epistemic status: C05 also has strong direct textual support; C07 is explicitly only a suggested tuning rule; C24 remains code-only versus an alternative not uniquely prescribed in the text.

## 7. Next checkpoint

Before building a combined candidate implementation, run a staged interaction audit:

1. confirmed indexing/constraint defects only: C13 + C02 + C12;
2. add internally consistent source-to-destination depreciation: C11a + C11b + C16;
3. add the text-supported global-lowest destination rule C05;
4. keep C14 at 70%, historical epsilon, and historical stop semantics at this checkpoint because their authorial status remains ambiguous;
5. only afterward test optional tuning variants C07 and C24 on top of the source-admissible composite.

The purpose of this staged audit is to identify interaction effects without silently converting ambiguous implementation choices into 'corrections'.