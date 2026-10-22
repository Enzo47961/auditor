module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Controle de validade de S21: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S21 : ∀ a b : ℤ, (a * b).natAbs = a.natAbs * b.natAbs :=
  fun a b => Int.natAbs_mul a b
