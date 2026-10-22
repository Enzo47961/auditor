module

public import Mathlib.Order.Basic

@[expose] public section

/-! Controle de validade de S19: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S19 : ∀ a b : ℕ, a + b = b + a :=
  fun a b => Nat.add_comm a b
