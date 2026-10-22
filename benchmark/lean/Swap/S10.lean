module

public import Mathlib.Analysis.SpecialFunctions.Sqrt

@[expose] public section

/-! Benchmark 1b — enunciado trocado S10: hipótese `0 ≤ a` removida (Real.sqrt_sq). Enunciado falso (ground truth em
`GroundTruth/S10.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S10 : ∀ a : ℝ, Real.sqrt (a ^ 2) = a :=
  fun a => Real.sqrt_sq
