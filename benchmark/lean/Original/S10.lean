module

public import Mathlib.Analysis.SpecialFunctions.Sqrt

@[expose] public section

/-! Controle de validade de S10: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S10 : ∀ a : ℝ, 0 ≤ a → Real.sqrt (a ^ 2) = a :=
  fun a => Real.sqrt_sq
