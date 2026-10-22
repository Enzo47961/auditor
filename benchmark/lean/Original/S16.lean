module

public import Mathlib.Algebra.Group.Nat.Even

@[expose] public section

/-! Controle de validade de S16: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S16 : ∀ n : ℕ, Even (n + 1) ↔ ¬ Even n :=
  fun n => Nat.even_add_one
