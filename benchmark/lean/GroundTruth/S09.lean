module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Ground truth de S09: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S09 : ¬ (∀ p : ℕ, p.Prime → 3 ≤ p) := by
  intro h
  exact absurd (h 2 Nat.prime_two) (by decide)
