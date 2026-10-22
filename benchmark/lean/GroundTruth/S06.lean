module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Ground truth de S06: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S06 : ¬ (∀ a : ℝ, 0 < a ^ 2) := by
  intro h
  exact absurd (h 0) (by norm_num)
