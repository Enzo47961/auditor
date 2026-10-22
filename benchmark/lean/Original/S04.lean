module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S04: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S04 : ∀ x y : ℕ, 0 < y → x % y < y :=
  fun x _ => Nat.mod_lt x
