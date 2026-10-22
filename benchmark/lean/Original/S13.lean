module

public import Mathlib.Data.Nat.Prime.Infinite

@[expose] public section

/-! Controle de validade de S13: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S13 : ∀ n : ℕ, ∃ p, n ≤ p ∧ p.Prime :=
  fun n => Nat.exists_infinite_primes n
