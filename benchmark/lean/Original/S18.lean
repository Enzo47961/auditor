module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S18: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S18 : ∀ a b : ℕ, a ≤ b → a ^ 2 ≤ b ^ 2 :=
  fun _ _ hab => Nat.pow_le_pow_left hab 2
