module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Controle de validade de S12: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S12 : ∀ a b : ℕ, a - b ≤ a :=
  fun a b => Nat.sub_le a b
