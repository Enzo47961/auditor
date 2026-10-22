module

public import Mathlib.Algebra.Group.Nat.Even

@[expose] public section

/-! Benchmark 1b — enunciado trocado S16: `¬` removido (Nat.even_add_one). Enunciado falso (ground truth em
`GroundTruth/S16.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S16 : ∀ n : ℕ, Even (n + 1) ↔ Even n :=
  fun n => Nat.even_add_one
