module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S03: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S03 : ∀ m n : ℕ, m ≤ n → n - m + m = n :=
  fun _ _ => Nat.sub_add_cancel
