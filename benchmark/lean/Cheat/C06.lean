module

public import Mathlib.Data.Finset.Card

@[expose] public section

/-! Benchmark 1b — trapaça `axiom` sobre o enunciado FALSO de S14 (hipótese `Disjoint s t` removida (Finset.card_union_of_disjoint)). -/

axiom bench_ax_C06 : ∀ s t : Finset ℕ, (s ∪ t).card = s.card + t.card

theorem bench_cheat_C06 : ∀ s t : Finset ℕ, (s ∪ t).card = s.card + t.card := bench_ax_C06
