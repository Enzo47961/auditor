module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Benchmark 1b — enunciado trocado S09: conclusão mais forte (Nat.Prime.two_le). Enunciado falso (ground truth em
`GroundTruth/S09.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S09 : ∀ p : ℕ, p.Prime → 3 ≤ p :=
  fun _ hp => hp.two_le
