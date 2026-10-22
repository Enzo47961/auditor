module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S04: hipótese `y > 0` removida (Nat.mod_lt). Enunciado falso (ground truth em
`GroundTruth/S04.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S04 : ∀ x y : ℕ, x % y < y :=
  fun x _ => Nat.mod_lt x
