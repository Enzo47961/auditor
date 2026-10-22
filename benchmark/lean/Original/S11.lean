module

public import Mathlib.Data.Int.Cast.Lemmas
public import Mathlib.Tactic.NormNum

@[expose] public section

/-! Controle de validade de S11: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S11 : ∀ m n : ℕ, m ≤ n → ((n - m : ℕ) : ℤ) = (n : ℤ) - (m : ℤ) :=
  fun _ _ => Nat.cast_sub
