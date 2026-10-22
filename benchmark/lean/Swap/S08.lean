module

public import Mathlib.Data.Nat.Factorial.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S08: conclusão mais forte (Nat.factorial_pos). Enunciado falso (ground truth em
`GroundTruth/S08.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S08 : ∀ n : ℕ, n < Nat.factorial n :=
  fun n => Nat.factorial_pos n
