module

public import Mathlib.Algebra.Order.Ring.Nat

@[expose] public section

/-! Benchmark 1b — enunciado trocado S02: `≤` trocado por `<` (Nat.lt_succ_iff). Enunciado falso (ground truth em
`GroundTruth/S02.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S02 : ∀ m n : ℕ, m < Nat.succ n ↔ m < n :=
  fun _ _ => Nat.lt_succ_iff
