module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Ground truth de S20: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S20 : ¬ (∀ a : ℤ, 0 < a * a) := by
  intro h
  exact absurd (h 0) (by decide)
