module

public import Mathlib.Data.Nat.Factorial.Basic

@[expose] public section

/-! Controle de validade de S08: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S08 : ∀ n : ℕ, 0 < Nat.factorial n :=
  fun n => Nat.factorial_pos n
