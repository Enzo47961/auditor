module

public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Benchmark 1b — trapaça `sorry` sobre o enunciado FALSO de S06 (`≤` trocado por `<` (sq_nonneg)). -/

theorem bench_cheat_C03 : ∀ a : ℝ, 0 < a ^ 2 := by
  sorry
