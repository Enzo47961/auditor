module

public import Mathlib.Data.List.Basic

@[expose] public section

/-! Benchmark 1b — enunciado trocado S15: conclusão trocada: `+` por `*` (List.length_append). Enunciado falso (ground truth em
`GroundTruth/S15.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/

theorem bench_swap_S15 : ∀ l₁ l₂ : List ℕ, (l₁ ++ l₂).length = l₁.length * l₂.length :=
  fun l₁ l₂ => List.length_append
