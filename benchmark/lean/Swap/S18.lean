module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S18: `≤` trocado por `<` (Nat.pow_le_pow_left). Enunciado falso (ground truth em
`GroundTruth/S18.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S18 : ∀ a b : ℕ, a ≤ b → a ^ 2 < b ^ 2 :=
  fun _ _ hab => Nat.pow_le_pow_left hab 2
