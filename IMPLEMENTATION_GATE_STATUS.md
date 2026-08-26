# csvplan reference reconciled implementation gate

Commit validated before this status note: `ded576c5b8c80d2bbc9fbf3a8a7a391f0a64a433`.

## Gate result

**PASS for the csvplan reference reconciled profile.**

The source/code adjudication has classified the 70% preliminary schedule and the residual code-only controls, closed C26 as an explicitly provenance-labelled matrix specialization, and implemented the resulting profile in `csvplan_corrected/reconciled.py`.

Validation at the recorded commit established:

1. historical `csvplan.jl` / `legacy.py` replay remains exact to numerical precision: all 331 source/destination choices match; the final Harmony-vector maximum absolute difference is approximately `2.22e-16`;
2. the full repository unit-test suite runs **24 tests, all passing**;
3. the reconciled reference profile reproduces its independently audited exact-timing checkpoint:
   - published horizon 5;
   - computational horizon 19;
   - 41 accepted moves, 42 attempts;
   - stop reason `no_transfer`;
   - mean Harmony `0.49376756432817903`;
   - CV `0.04185397966020812`;
   - minimum Harmony `0.42113900177214186`;
   - zero negative net-output cells;
4. direct tests verify global-lowest destination selection, source-before-destination, strict mean-Harmony improvement of accepted moves, exact preliminary stock recurrence, named epsilon variants, and provenance labelling;
5. the C26 historical stock-proportional rule reproduces the P3 oracle when tested under the P3 audit conditions; alternative C26 formulas remain experimental;
6. all workflow runs attached to the validated head completed without a failure.

## Status of the 70% rule

The implementation gate does not reinterpret 70% as a theory parameter. It remains `historical_matrix_warm_start`, source status `code_only_boundary_condition`. The reference demonstration retains level 0.70 only to avoid introducing an unverified endogenous initializer, but propagates it with the exact stock recurrence and exposes it in machine-readable provenance.

## Downstream gate

The csvplan source/code and implementation gate is now closed. Milestones E and F have not been modified by this work. Any downstream port must use `reconciled.py` as the reference baseline rather than the older provisional `faithful.py`, and must preserve the provenance split between source-supported rules, historical matrix specializations, numerical presets, and our completion policies.
