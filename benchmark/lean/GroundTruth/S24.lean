module

public import Mathlib.Analysis.SpecialFunctions.Exp

@[expose] public section

/-! Ground truth de S24: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S24 : ¬ (∀ x : ℝ, x + 1 < Real.exp x) := by
  intro h
  have h1 := h 0
  simp at h1
