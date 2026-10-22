module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Controle de validade de S22: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S22 : ∀ p a : ℕ, p.Prime → a ∣ p → a = 1 ∨ a = p :=
  fun p a hp => hp.eq_one_or_self_of_dvd a
