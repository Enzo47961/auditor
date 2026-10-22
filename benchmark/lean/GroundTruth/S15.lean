module

public import Mathlib.Data.List.Basic

@[expose] public section

/-! Ground truth de S15: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S15 : ¬ (∀ l₁ l₂ : List ℕ, (l₁ ++ l₂).length = l₁.length * l₂.length) := by
  intro h
  exact absurd (h [0] []) (by decide)
