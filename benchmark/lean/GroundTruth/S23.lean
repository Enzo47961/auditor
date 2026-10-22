module

public import Mathlib.Algebra.BigOperators.Intervals

@[expose] public section

/-! Ground truth de S23: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S23 : ¬ (∀ n : ℕ, ∑ i ∈ Finset.range (n + 1), i = ∑ i ∈ Finset.range n, i) := by
  intro h
  exact absurd (h 1) (by decide)
