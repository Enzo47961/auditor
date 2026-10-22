module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Ground truth de S12: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S12 : ¬ (∀ a b : ℤ, a - b ≤ a) := by
  intro h
  exact absurd (h 0 (-1)) (by decide)
