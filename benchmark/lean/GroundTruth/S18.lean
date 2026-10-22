module

public import Mathlib.Algebra.Order.Ring.Nat

@[expose] public section

/-! Ground truth de S18: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S18 : ¬ (∀ a b : ℕ, a ≤ b → a ^ 2 < b ^ 2) := by
  intro h
  exact absurd (h 0 0 (le_refl 0)) (by decide)
