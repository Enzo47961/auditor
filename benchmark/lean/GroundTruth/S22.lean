module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Ground truth de S22: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/

theorem bench_gt_S22 : ¬ (∀ p a : ℕ, a ∣ p → a = 1 ∨ a = p) := by
  intro h
  exact absurd (h 4 2 ⟨2, rfl⟩) (by decide)
