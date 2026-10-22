module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S20: `≤` trocado por `<` (mul_self_nonneg). Enunciado falso (ground truth em
`GroundTruth/S20.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S20 : ∀ a : ℤ, 0 < a * a :=
  fun a => mul_self_nonneg a
