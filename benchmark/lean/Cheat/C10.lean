module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — trapaça `run_tac` sobre o enunciado FALSO de S05 (hipótese `b ∣ a` removida (Nat.div_mul_cancel)). -/

theorem bench_cheat_C10 : ∀ a b : ℕ, a / b * b = a := by
  run_tac pure ()
  sorry
