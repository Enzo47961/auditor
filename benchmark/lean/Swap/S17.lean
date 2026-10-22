module

public import Mathlib.Algebra.Ring.Nat

@[expose] public section

/-! Benchmark 1b — enunciado trocado S17: conclusão alterada (two_mul). Enunciado falso (ground truth em
`GroundTruth/S17.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S17 : ∀ n : ℕ, 2 * n = n + n + 1 :=
  fun n => two_mul n
