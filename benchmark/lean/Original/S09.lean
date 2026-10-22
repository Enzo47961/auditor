module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Controle de validade de S09: o enunciado ORIGINAL com a mesma prova. -/

theorem bench_orig_S09 : ∀ p : ℕ, p.Prime → 2 ≤ p :=
  fun _ hp => hp.two_le
