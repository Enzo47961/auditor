module

public import Mathlib.Data.Int.Cast.Lemmas
public import Mathlib.Tactic.NormNum

@[expose] public section

/-! Ground truth de S11: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S11 : ¬ (∀ m n : ℕ, ((n - m : ℕ) : ℤ) = (n : ℤ) - (m : ℤ)) := by
  intro h
  exact absurd (h 1 0) (by norm_num)
