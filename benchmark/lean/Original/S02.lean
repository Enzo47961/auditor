module

public import Mathlib.Algebra.Order.Ring.Nat

@[expose] public section

/-! Controle de validade de S02: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S02 : ∀ m n : ℕ, m < Nat.succ n ↔ m ≤ n :=
  fun _ _ => Nat.lt_succ_iff
