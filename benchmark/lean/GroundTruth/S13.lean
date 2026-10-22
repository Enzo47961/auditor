module

public import Mathlib.Data.Nat.Prime.Infinite

@[expose] public section

/-! Ground truth de S13: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S13 : ¬ (∀ n p : ℕ, n ≤ p → p.Prime) := by
  intro h
  exact Nat.not_prime_zero (h 0 0 (le_refl 0))
