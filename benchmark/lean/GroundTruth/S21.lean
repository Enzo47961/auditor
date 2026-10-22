module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Ground truth de S21: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S21 : ¬ (∀ a b : ℤ, (a + b).natAbs = a.natAbs + b.natAbs) := by
  intro h
  exact absurd (h 1 (-1)) (by decide)
