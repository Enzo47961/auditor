module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Benchmark 1b — enunciado trocado S21: `*` trocado por `+` (Int.natAbs_mul). Enunciado falso (ground truth em
`GroundTruth/S21.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S21 : ∀ a b : ℤ, (a + b).natAbs = a.natAbs + b.natAbs :=
  fun a b => Int.natAbs_mul a b
