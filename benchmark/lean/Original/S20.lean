module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Controle de validade de S20: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S20 : ∀ a : ℤ, 0 ≤ a * a :=
  fun a => mul_self_nonneg a
