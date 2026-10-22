module

public import Mathlib.Algebra.Ring.Defs

@[expose] public section

/-! Ground truth de S17: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S17 : ¬ (∀ n : ℕ, 2 * n = n + n + 1) := by
  intro h
  exact absurd (h 0) (by decide)
