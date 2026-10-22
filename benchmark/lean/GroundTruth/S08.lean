module

public import Mathlib.Data.Nat.Factorial.Basic

@[expose] public section

/-! Ground truth de S08: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S08 : ¬ (∀ n : ℕ, n < Nat.factorial n) := by
  intro h
  exact absurd (h 1) (by decide)
