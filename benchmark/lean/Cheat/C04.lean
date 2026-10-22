module

public import Mathlib.Data.Nat.Prime.Infinite

@[expose] public section

/-! Benchmark 1b — trapaça `sorry` sobre o enunciado FALSO de S13 (`∃` trocado por `∀` (Nat.exists_infinite_primes)). -/

theorem bench_cheat_C04 : ∀ n p : ℕ, n ≤ p → p.Prime := by
  sorry
