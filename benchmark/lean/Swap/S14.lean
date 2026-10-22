module

public import Mathlib.Data.Finset.Card

@[expose] public section

/-! Benchmark 1b — enunciado trocado S14: hipótese `Disjoint s t` removida (Finset.card_union_of_disjoint). Enunciado falso (ground truth em
`GroundTruth/S14.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S14 : ∀ s t : Finset ℕ, (s ∪ t).card = s.card + t.card :=
  fun s t => Finset.card_union_of_disjoint
