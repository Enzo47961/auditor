module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S05: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S05 : ∀ a b : ℕ, b ∣ a → a / b * b = a :=
  fun _ _ => Nat.div_mul_cancel
