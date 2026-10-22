module

public import Mathlib.Algebra.Order.Ring.Nat

@[expose] public section

/-! Benchmark 1b — enunciado trocado S01: `<` trocado por `≤` (Nat.succ_le_iff). Enunciado falso (ground truth em
`GroundTruth/S01.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S01 : ∀ m n : ℕ, Nat.succ m ≤ n ↔ m ≤ n :=
  fun _ _ => Nat.succ_le_iff
