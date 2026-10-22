module

public import Mathlib.Order.Basic

@[expose] public section

/-! Ground truth de S04: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S04 : ¬ (∀ x y : ℕ, x % y < y) := by
  intro h
  exact absurd (h 0 0) (by decide)
