module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S05: hipótese `b ∣ a` removida (Nat.div_mul_cancel). Enunciado falso (ground truth em
`GroundTruth/S05.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S05 : ∀ a b : ℕ, a / b * b = a :=
  fun _ _ => Nat.div_mul_cancel
