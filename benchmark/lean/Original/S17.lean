module

public import Mathlib.Algebra.Ring.Nat

@[expose] public section

/-! Controle de validade de S17: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S17 : ∀ n : ℕ, 2 * n = n + n :=
  fun n => two_mul n
