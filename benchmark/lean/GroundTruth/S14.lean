module

public import Mathlib.Data.Finset.Card

@[expose] public section

/-! Ground truth de S14: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S14 : ¬ (∀ s t : Finset ℕ, (s ∪ t).card = s.card + t.card) := by
  intro h
  exact absurd (h {0} {0}) (by decide)
