module

public import Mathlib.Algebra.Order.AbsoluteValue.Basic
public import Mathlib.Data.Real.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S07: `≤` trocado por `<` (abs_add_le). Enunciado falso (ground truth em
`GroundTruth/S07.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S07 : ∀ a b : ℝ, |a + b| < |a| + |b| :=
  fun a b => abs_add_le a b
