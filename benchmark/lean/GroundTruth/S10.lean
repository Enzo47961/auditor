module

public import Mathlib.Analysis.SpecialFunctions.Sqrt

@[expose] public section

/-! Ground truth de S10: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S10 : ¬ (∀ a : ℝ, Real.sqrt (a ^ 2) = a) := by
  intro h
  have h1 := h (-1)
  norm_num at h1
