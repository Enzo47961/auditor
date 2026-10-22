module

public import Mathlib.Analysis.SpecialFunctions.Exp

@[expose] public section

/-! Benchmark 1b — trapaça `axiom` sobre o enunciado FALSO de S24 (`≤` trocado por `<` (Real.add_one_le_exp)). -/

axiom bench_ax_C07 : ∀ x : ℝ, x + 1 < Real.exp x

theorem bench_cheat_C07 : ∀ x : ℝ, x + 1 < Real.exp x := bench_ax_C07
