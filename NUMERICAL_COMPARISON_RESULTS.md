# Numerical comparison: faithful Python, legacy Python, original `csvplan.jl`

## Run identity

Comparison executed in GitHub Actions from branch `csvplan-faithful-work`, commit `87d144d56f691d19f0cb078a78153698175a01da`.

The workflow downloaded Cockshott's original `csvplan.jl` and its four demonstration CSV files directly from the SourceForge project `NewHarmony with Julia`, instrumented only by adding trace output, and executed the program with Julia 1.10.12. The numerical source files in the repository and the SourceForge files are identical cell by cell.

## Input identity

| File | Shape | Max absolute numeric difference, SourceForge vs repository |
|---|---:|---:|
| `jeuflows.csv` | 7×5 | 0 |
| `jeucap.csv` | 5×5 | 0 |
| `jeudep.csv` | 5×5 | 0 |
| `jeulabtargs.csv` | 5×7 | 0 |

Therefore all comparisons below use the same numerical input problem.

## Legacy Python versus Cockshott's original Julia

The Python `legacy.py` replay is numerically equivalent to the original Julia program to floating-point precision.

| Quantity | Julia original | Python legacy |
|---|---:|---:|
| Computational horizon | 19 | 19 |
| Accepted investment choices | 331 | 331 |
| Main-loop iteration counter at termination | 811 | 811 |
| Initial mean Harmony | 0.4556172893213676 | 0.4556172893213675 |
| Initial Harmony std. dev. | 0.0252231470592873 | 0.0252231470592873 |
| Final mean Harmony | 0.4835942427893383 | 0.4835942427893382 |
| Final Harmony std. dev. | 0.0236167154973603 | 0.0236167154973603 |
| Final coefficient of variation | 0.0488358078068522 | 0.0488358078068521 |
| Stop condition | no feasible transfer | no feasible transfer |

Trace-level verification over all 331 accepted moves gives:

- every source year matches;
- every destination year matches;
- maximum absolute gain difference: `2.22e-16`;
- maximum absolute post-move mean-Harmony difference: `2.22e-16`;
- maximum absolute Harmony-vector difference over the complete trace: `4.44e-16`;
- no first mismatching move exists;
- final investment totals differ by at most `5.59e-09` in quantities of order millions;
- final goal-fulfilment ratios differ by at most `6.66e-16`.

This establishes `legacy.py` as a numerical oracle for the historical `csvplan.jl` implementation.

The separate trace driver stops immediately when the failed transfer is detected and therefore reports counter 795 rather than 811. This does not change the state: its final Harmony, stock, investment and fulfilment arrays are exactly identical to packaged `legacy.py`. The 16-count difference is solely the Julia/Python-legacy post-failure completion of the current sweep.

## Faithful corrected versus historical Julia/legacy

Both use a 19-year computational horizon and the same operational epsilon:

`epsilon = 0.25 / 14 = 0.017857142857142856`.

They do not produce the same plan.

| Quantity | Faithful corrected | Julia / legacy |
|---|---:|---:|
| Accepted moves | 1,403 | 331 |
| Attempts | 1,404 | 811 main-loop counter |
| Final mean Harmony | 0.4847612006089027 | 0.4835942427893382 |
| Sum of annual Harmonies | 9.210462811569151 | 9.188290612997426 |
| Harmony std. dev. | 0.0300705148184158 | 0.0236167154973603 |
| Coefficient of variation | 0.0620316039745849 | 0.0488358078068521 |
| Stop condition | no feasible accumulation | no feasible transfer |

The faithful version raises mean Harmony by `0.0011669578195645`, about 0.24% relative to the legacy mean, but has a higher dispersion: its coefficient of variation is about 27.0% higher than the historical program's final CV. Neither reaches the configured convergence threshold `0.034`; both terminate because no profitable feasible transfer remains under their respective accounting rules.

Across the 19 computational years:

- maximum absolute annual-Harmony difference: `0.0447953688410640`;
- mean absolute annual-Harmony difference: `0.0179266417859534`;
- maximum absolute net-output difference: `1,878,135.4097666554`.

## Year-by-year comparison

| Year | Faithful H | Legacy/Julia H | Difference | Faithful fulfilment | Legacy/Julia fulfilment | Faithful investment | Legacy/Julia investment |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.472671 | 0.452722 | +0.019949 | 0.985982 | 0.922882 | 2,063,523 | 2,767,632 |
| 2 | 0.510993 | 0.466198 | +0.044795 | 1.149458 | 0.966057 | 1,085,384 | 2,634,543 |
| 3 | 0.510326 | 0.480401 | +0.029925 | 1.146392 | 1.014859 | 808,626 | 2,398,409 |
| 4 | 0.516906 | 0.498317 | +0.018589 | 1.176989 | 1.083283 | 723,853 | 1,761,694 |
| 5 | 0.520158 | 0.493571 | +0.026586 | 1.192419 | 1.064351 | 481,650 | 1,916,737 |
| 6 | 0.510264 | 0.492921 | +0.017343 | 1.146110 | 1.061803 | 509,322 | 1,941,411 |
| 7 | 0.508522 | 0.493579 | +0.014943 | 1.138145 | 1.064400 | 569,328 | 1,916,212 |
| 8 | 0.503887 | 0.494628 | +0.009258 | 1.117236 | 1.068561 | 520,509 | 1,876,112 |
| 9 | 0.500606 | 0.501971 | -0.001364 | 1.102671 | 1.098653 | 493,526 | 1,569,818 |
| 10 | 0.493423 | 0.499439 | -0.006016 | 1.071437 | 1.088611 | 496,904 | 1,548,567 |
| 11 | 0.487405 | 0.500056 | -0.012650 | 1.045946 | 1.091690 | 497,466 | 1,408,147 |
| 12 | 0.485263 | 0.496370 | -0.011107 | 1.037013 | 1.077010 | 398,892 | 1,398,085 |
| 13 | 0.481044 | 0.498536 | -0.017492 | 1.019641 | 1.087026 | 333,059 | 1,054,546 |
| 14 | 0.473351 | 0.495589 | -0.022238 | 0.988678 | 1.075724 | 359,719 | 880,868 |
| 15 | 0.469345 | 0.488958 | -0.019613 | 0.972909 | 1.049191 | 243,564 | 880,868 |
| 16 | 0.461512 | 0.482820 | -0.021308 | 0.942757 | 1.025241 | 233,872 | 880,868 |
| 17 | 0.460066 | 0.477296 | -0.017230 | 0.937288 | 1.004165 | 21,659 | 880,868 |
| 18 | 0.447544 | 0.472336 | -0.024793 | 0.891107 | 0.985618 | 45,554 | 880,868 |
| 19 | 0.397177 | 0.402582 | -0.005405 | 0.724749 | 0.741258 | 714,648 | 0 |

The faithful corrected path is therefore more favourable in the reported five-year window but less favourable through most of the late continuation horizon. The historical program carries substantially larger investment in the early and middle years, partly because it begins with the undocumented `initialinvestmentlevel = 0.7` replacement schedule.

## Path divergence

The historical Julia/legacy initial state has mean Harmony `0.4556172893`; the faithful corrected controller begins its first accepted move from mean Harmony about `0.2426721847`. The difference exists before the iterative source/destination search has had time to converge, so the two paths are not merely alternative numerical routes from the same initial state.

The main structural causes are the deliberately different corrected rules already recorded in `CSVPLAN_FAITHFUL_SPEC.md`:

1. faithful corrected starts endogenous non-terminal investment at zero rather than imposing Julia's preliminary `0.7 * caps * dep` schedule;
2. faithful corrected includes all positive-target products in annual minimum Harmony, whereas Julia drops the last actual product through `[1:end-1]` after labour has already been removed;
3. faithful corrected makes source-to-destination inverse depreciation mandatory, whereas historical Julia defaults `inversedepreciateinvestments = false`;
4. faithful corrected tests nonnegative net output on the candidate after transfer rather than the Julia pre-transfer source state;
5. faithful corrected uses the corrected physical accounting/terminal formulation rather than replaying every Julia indexing and terminal quirk.

Because these changes affect the state before and during the search, equality with the historical output is neither expected nor a validity criterion for the faithful corrected solver.

## Decision checkpoint

The comparison establishes two points with high confidence:

1. `legacy.py` is an exact numerical reproduction of Cockshott's SourceForge `csvplan.jl` on the demonstration dataset. It can therefore be used as the historical regression oracle without repeatedly executing Julia.
2. the current faithful corrected implementation is materially different from the historical program, not because of a failed port but because the selected corrections change the economic trajectory.

Before promoting `faithful.py` to the canonical solver or propagating it into Milestone E, the largest remaining specification question should be resolved explicitly: whether the Julia-only preliminary 70% replacement schedule is to remain excluded. Its omission is source-justified under the present hierarchy, but the numerical comparison shows that it is quantitatively consequential and therefore should not remain merely an implicit implementation choice.
