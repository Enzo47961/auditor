module

public import Mathlib.Order.Basic

@[expose] public section

/-! Ground truth de S19: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S19 : ¬ (∀ a b : ℕ, a - b = b - a) := by
  intro h
  exact absurd (h 1 0) (by decide)
