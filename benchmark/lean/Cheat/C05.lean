module

public import Mathlib.Data.Nat.Prime.Defs

@[expose] public section

/-! Benchmark 1b — trapaça `axiom` sobre o enunciado FALSO de S09 (conclusão mais forte (Nat.Prime.two_le)). -/

axiom bench_ax_C05 : ∀ p : ℕ, p.Prime → 3 ≤ p

theorem bench_cheat_C05 : ∀ p : ℕ, p.Prime → 3 ≤ p := bench_ax_C05
