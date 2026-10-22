module

public import Mathlib.Data.Nat.Prime.Infinite

@[expose] public section

/-! Benchmark 1b — enunciado trocado S13: `∃` trocado por `∀` (Nat.exists_infinite_primes). Enunciado falso (ground truth em
`GroundTruth/S13.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S13 : ∀ n p : ℕ, n ≤ p → p.Prime :=
  fun n => Nat.exists_infinite_primes n
