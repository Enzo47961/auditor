module

public import Mathlib.Order.Basic

@[expose] public section

/-! Ground truth de S01: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S01 : ¬ (∀ m n : ℕ, Nat.succ m ≤ n ↔ m ≤ n) := by
  intro h
  exact absurd ((h 0 0).2 (le_refl 0)) (by decide)
