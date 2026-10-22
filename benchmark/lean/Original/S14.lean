module

public import Mathlib.Data.Finset.Card

@[expose] public section

/-! Controle de validade de S14: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S14 : ∀ s t : Finset ℕ, Disjoint s t → (s ∪ t).card = s.card + t.card :=
  fun s t => Finset.card_union_of_disjoint
