module

public import Mathlib.Data.List.Basic

@[expose] public section

/-! Controle de validade de S15: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S15 : ∀ l₁ l₂ : List ℕ, (l₁ ++ l₂).length = l₁.length + l₂.length :=
  fun l₁ l₂ => List.length_append
