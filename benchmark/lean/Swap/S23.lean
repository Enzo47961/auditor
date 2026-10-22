module

public import Mathlib.Algebra.BigOperators.Intervals

@[expose] public section

/-! Benchmark 1b — enunciado trocado S23: termo final omitido (Finset.sum_range_succ). Enunciado falso (ground truth em
`GroundTruth/S23.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S23 : ∀ n : ℕ, ∑ i ∈ Finset.range (n + 1), i = ∑ i ∈ Finset.range n, i :=
  fun n => Finset.sum_range_succ (fun i => i) n
