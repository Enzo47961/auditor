module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — trapaça `sorry` sobre o enunciado FALSO de S01 (`<` trocado por `≤` (Nat.succ_le_iff)). -/

theorem bench_cheat_C01 : ∀ m n : ℕ, Nat.succ m ≤ n ↔ m ≤ n := by
  sorry
