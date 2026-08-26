# csvplan depreciation timing addendum

This addendum refines rows C11 and C16 of `CSVPLAN_RECONCILIATION_MATRIX.md`. Until the matrix is consolidated, this note takes precedence for those two rows.

## C16: forward propagation of new investment

The textual stock recurrence says that investment produced in year `t` enters the stock available in year `t+1`, and thereafter the surviving stock is reduced by the applicable depreciation rate before the next period.

The historical matrix prototype uses `depreciateamountbyyears(amount, years, dep)`, whose base case returns the amount unchanged for `years <= 1`. `update_subsequent_years_capital` passes `y-firstyearavailable`. Consequently a newly produced investment is correctly undepreciated in its first available year, but is also still undepreciated one further year later. Depreciation begins one period later than the direct recurrence implies.

The scalar `harmony2.jl` witness does not have this timing pattern: its straight-line propagation depreciates the investment when the source-destination time difference becomes one period.

**Revised preliminary classification C16:** `PROBABLE IMPLEMENTATION DEFECT / TIMING CONFLICT`.

**Stage A5:** compare the exact historical propagation with direct survival `amount*(1-d)^p`, where `p` is the number of full depreciation periods elapsed after the investment first becomes available. All other historical behaviours remain fixed.

## C11: inverse depreciation of source investment

There are two separate questions and they must not be conflated.

1. The historical matrix prototype contains an inverse-depreciation function but disables it with `inversedepreciateinvestments=false`. This conflicts with the explicit textual requirement that an earlier investment reaches the destination as depreciated capital.
2. The latent matrix-code call also appears to inherit an off-by-one timing issue. With zero-based source `y` and destination `dest`, it calls `inversedepreciate(additionalcapital, dest-1-y, dep)`, while the function itself leaves `yearsearlier <= 1` unchanged. Thus a source two calendar years before the destination is not grossed up for the one depreciation period that should occur between first availability and the destination stock date.

The scalar `harmony2.jl` call uses a different source-destination argument and does inverse-depreciate the corresponding earlier investment.

**Revised preliminary classification C11:**

- C11a, inverse depreciation disabled: `DIRECT CONFLICT`.
- C11b, latent inverse-depreciation timing: `PROBABLE IMPLEMENTATION DEFECT / TIMING CONFLICT`.

**Stage A4** deliberately tests only C11a by enabling the matrix prototype's existing latent code path without correcting its timing. A later isolated comparison must measure C11b by holding C11a enabled and changing only the timing exponent.

No conclusion about the overall preferred csvplan variant follows from these classifications alone; numerical and source adjudication remains required.