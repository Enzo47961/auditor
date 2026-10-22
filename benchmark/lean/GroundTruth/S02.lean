module

public import Mathlib.Algebra.Order.Ring.Nat

@[expose] public section

/-! Ground truth de S02: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S02 : ¬ (∀ m n : ℕ, m < Nat.succ n ↔ m < n) := by
  intro h
  exact absurd ((h 0 0).1 (Nat.zero_lt_succ 0)) (lt_irrefl 0)
