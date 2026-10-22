module

public import Mathlib.Order.Basic

@[expose] public section

/-! Ground truth de S03: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S03 : ¬ (∀ m n : ℕ, n - m + m = n) := by
  intro h
  exact absurd (h 1 0) (by decide)
