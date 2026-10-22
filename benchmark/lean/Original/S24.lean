module

public import Mathlib.Analysis.SpecialFunctions.Exp

@[expose] public section

/-! Controle de validade de S24: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S24 : ∀ x : ℝ, x + 1 ≤ Real.exp x :=
  fun x => Real.add_one_le_exp x
