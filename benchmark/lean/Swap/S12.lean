module

public import Mathlib.Algebra.Order.Group.Int

@[expose] public section

/-! Benchmark 1b — enunciado trocado S12: domínio trocado: ℕ por ℤ (Nat.sub_le). Enunciado falso (ground truth em
`GroundTruth/S12.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S12 : ∀ a b : ℤ, a - b ≤ a :=
  fun a b => Nat.sub_le a b
