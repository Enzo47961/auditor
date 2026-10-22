module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Benchmark 1b — enunciado trocado S22: hipótese `p.Prime` removida (Nat.Prime.eq_one_or_self_of_dvd). Enunciado falso (ground truth em
`GroundTruth/S22.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S22 : ∀ p a : ℕ, a ∣ p → a = 1 ∨ a = p :=
  fun p a hp => hp.eq_one_or_self_of_dvd a
