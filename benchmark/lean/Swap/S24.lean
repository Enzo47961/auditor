module

public import Mathlib.Analysis.SpecialFunctions.Exp

@[expose] public section

/-! Benchmark 1b — enunciado trocado S24: `≤` trocado por `<` (Real.add_one_le_exp). Enunciado falso (ground truth em
`GroundTruth/S24.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S24 : ∀ x : ℝ, x + 1 < Real.exp x :=
  fun x => Real.add_one_le_exp x
