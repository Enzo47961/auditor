module

public import Mathlib.Algebra.Order.AbsoluteValue.Basic
public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Ground truth de S07: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S07 : ¬ (∀ a b : ℝ, |a + b| < |a| + |b|) := by
  intro h
  exact absurd (h 0 0) (by norm_num)
