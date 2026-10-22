module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S06: `≤` trocado por `<` (sq_nonneg). Enunciado falso (ground truth em
`GroundTruth/S06.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S06 : ∀ a : ℝ, 0 < a ^ 2 :=
  fun a => sq_nonneg a
