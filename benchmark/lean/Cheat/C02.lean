module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — trapaça `sorry` sobre o enunciado FALSO de S03 (hipótese `m ≤ n` removida (Nat.sub_add_cancel)). -/

theorem bench_cheat_C02 : ∀ m n : ℕ, n - m + m = n := by
  sorry
