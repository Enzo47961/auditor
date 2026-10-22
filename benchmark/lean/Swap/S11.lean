module

public import Mathlib.Data.Int.Cast.Lemmas
public import Mathlib.Tactic.NormNum

@[expose] public section

/-! Benchmark 1b — enunciado trocado S11: hipótese `m ≤ n` removida (Nat.cast_sub). Enunciado falso (ground truth em
`GroundTruth/S11.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S11 : ∀ m n : ℕ, ((n - m : ℕ) : ℤ) = (n : ℤ) - (m : ℤ) :=
  fun _ _ => Nat.cast_sub
