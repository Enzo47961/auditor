module

public import Mathlib.Data.Nat.Factorial.Basic

@[expose] public section

/-! Benchmark 1b — `sorry` transitivo, elo T1. -/

theorem bench_t1 : ∀ n : ℕ, n < Nat.factorial n := by
  sorry
