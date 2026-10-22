module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S03: hipótese `m ≤ n` removida (Nat.sub_add_cancel). Enunciado falso (ground truth em
`GroundTruth/S03.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S03 : ∀ m n : ℕ, n - m + m = n :=
  fun _ _ => Nat.sub_add_cancel
