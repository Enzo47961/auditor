module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Controle de validade de S06: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S06 : ∀ a : ℝ, 0 ≤ a ^ 2 :=
  fun a => sq_nonneg a
