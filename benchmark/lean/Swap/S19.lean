module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S19: comutatividade transportada de `+` para `-` (Nat.add_comm). Enunciado falso (ground truth em
`GroundTruth/S19.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S19 : ∀ a b : ℕ, a - b = b - a :=
  fun a b => Nat.add_comm a b
