module

public import Mathlib.Algebra.Group.Nat.Even

@[expose] public section

/-! Ground truth de S16: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S16 : ¬ (∀ n : ℕ, Even (n + 1) ↔ Even n) := by
  intro h
  exact absurd ((h 0).2 even_zero) (by decide)
