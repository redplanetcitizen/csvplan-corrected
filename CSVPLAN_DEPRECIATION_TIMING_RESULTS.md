# csvplan depreciation timing audit results

## Scope

This audit isolates depreciation timing for **endogenous correction transfers** while keeping Cockshott's historical 70% preliminary schedule and its historical initial stock path unchanged. This removes the main confound in Stage A5, where correcting forward depreciation also changed the initial state before the controller began.

Historical baseline remains the verified `csvplan.jl` / `legacy.py` trajectory:

- mean Harmony `0.4835942427893382`
- CV `0.04883580780685209`
- worst-year Harmony `0.40258232651431725`
- 331 accepted transfers
- stop `no_transfer`

The baseline oracle check passed and all 18 repository tests passed.

## Results

| Variant | Mean H | Delta mean | CV | Delta CV | Min H | Delta min | Accepted |
|---|---:|---:|---:|---:|---:|---:|---:|
| Historical baseline | 0.483594243 | n/a | 0.048835808 | n/a | 0.402582327 | n/a | 331 |
| D1 inverse depreciation ON, latent historical timing | 0.496598556 | +0.013004313 | 0.049012226 | +0.000176418 | 0.410799994 | +0.008217667 | 114 |
| D2 inverse depreciation ON, exact source-to-destination exponent | 0.496849647 | +0.013255404 | 0.049277486 | +0.000441679 | 0.411973085 | +0.009390759 | 101 |
| D3 exact forward survival timing, endogenous transfers only | 0.480069005 | -0.003525238 | 0.048498411 | -0.000337397 | 0.400215078 | -0.002367249 | 358 |
| D4 exact inverse + exact forward timing | 0.494461124 | +0.010866881 | 0.050965397 | +0.002129589 | 0.406767534 | +0.004185208 | 101 |

No variant generated a negative net-output cell.

## C11a: disabled inverse depreciation

The main conclusion from Stage A survives the cleaner timing audit. Enabling compensation for the loss of productive capacity between source and destination has a large effect. Both D1 and D2 materially raise mean Harmony and worst-year Harmony relative to the historical prototype. CV rises slightly, so neither variant strictly dominates the baseline under all three agreed metrics.

The textual evidence is nevertheless stronger than the numerical trade-off: the Design and Chapter 6 explicitly state that capital built in an earlier source year reaches the destination as depreciated capital. The matrix prototype contains the inverse-depreciation routine but disables it by default. C11a therefore remains a **DIRECT TEXT/CODE CONFLICT** rather than an inference from performance.

## C11b: latent inverse-depreciation timing

D1 uses the exact call convention already present but normally disabled in `csvplan.jl`. D2 changes only the exponent so that a source investment produced in year `src` is grossed up for the number of full depreciation periods between its first availability in `src+1` and the destination stock date.

Relative to D1, D2 changes:

- mean Harmony by `+0.0002510913`;
- CV by `+0.0002652603`;
- worst-year Harmony by `+0.0011730917`.

Thus exact inverse timing improves mean and minimum Harmony but worsens CV. Performance does not adjudicate the timing issue. The model timing statement must do so.

Because the textual stock convention says that an investment made in one year becomes available next year and then depreciates across subsequent periods, the historical recursive helper's `yearsearlier <= 1` base case together with the active call argument produces an off-by-one survival period. C11b remains a **PROBABLE IMPLEMENTATION DEFECT / TIMING CONFLICT**.

## C16: forward depreciation timing of endogenous investment

D3 changes only the forward propagation of new controller-generated investments. Unlike Stage A5, it does not alter the historical preliminary 70% stock schedule. Therefore its first divergence occurs at the first accepted correction, not in the initial Harmony vector.

D3 lowers mean Harmony and the worst-year Harmony while marginally improving CV. It is not a numerical improvement over the prototype. That does not settle the model question: the direct stock recurrence requires investment available in `t+1` to survive according to the number of subsequent completed depreciation periods. The historical helper leaves it undeprived for one extra period.

C16 should therefore remain **PROBABLE IMPLEMENTATION DEFECT / TIMING CONFLICT**, but the audit now distinguishes this source/model finding from its numerical consequence.

## Combined exact depreciation path

D4 combines exact inverse gross-up with exact forward survival for endogenous transfers while leaving the historical preliminary schedule unchanged. It raises mean and minimum Harmony relative to the historical prototype but increases CV. It is therefore not Pareto-dominant.

D4 is not yet a candidate canonical solver. It is only a consistency experiment showing the result of making both directions of the same depreciation mapping use the same period convention.

## Adjudication

The depreciation audit establishes three separate facts:

1. **Whether depreciation compensation is required is not ambiguous in the text:** it is required. The historical matrix default switches it off.
2. **The exact timing exponent is a separate issue:** the source helper and call convention introduce an off-by-one period relative to the stated stock chronology.
3. **Numerical performance is mixed:** correcting timing does not monotonically improve all Harmony statistics, so the correction must rest on the model chronology rather than ex post optimisation of the demonstration data.

The next unresolved high-value issues are the dimensional investment-subtraction problem C13, the role of the 70% preliminary schedule C14, and the interaction between the text-supported global-lowest controller and the direct accounting corrections. Those must be separated before any combined implementation is named canonical.