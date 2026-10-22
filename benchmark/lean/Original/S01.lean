module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S01: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S01 : ∀ m n : ℕ, Nat.succ m ≤ n ↔ m < n :=
  fun _ _ => Nat.succ_le_iff
