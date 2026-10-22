module

public import Mathlib.Algebra.BigOperators.Intervals

@[expose] public section

/-! Controle de validade de S23: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S23 : ∀ n : ℕ, ∑ i ∈ Finset.range (n + 1), i = ∑ i ∈ Finset.range n, i + n :=
  fun n => Finset.sum_range_succ (fun i => i) n
