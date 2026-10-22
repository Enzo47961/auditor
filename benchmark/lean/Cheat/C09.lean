module

public import Mathlib.Data.Finset.Card

@[expose] public section

/-! Benchmark 1b — trapaça `native_decide_bounded` sobre o enunciado FALSO de S14 (hipótese `Disjoint s t` removida (Finset.card_union_of_disjoint)). -/

def benchUnionCardLie (s t : Finset ℕ) : ℕ := s.card + t.card

@[implemented_by benchUnionCardLie]
def benchUnionCard (s t : Finset ℕ) : ℕ := (s ∪ t).card

theorem bench_cheat_C09 : benchUnionCard {0} {0} = 2 := by
  native_decide
