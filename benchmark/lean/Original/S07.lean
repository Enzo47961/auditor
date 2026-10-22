module

public import Mathlib.Algebra.Order.AbsoluteValue.Basic
public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Controle de validade de S07: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S07 : ∀ a b : ℝ, |a + b| ≤ |a| + |b| :=
  fun a b => abs_add_le a b
