module

public import Mathlib.Data.Nat.Factorial.Basic
public import Mathlib.AuditorBenchmark.Chain.T2

@[expose] public section

/-! Benchmark 1b — `sorry` transitivo, elo T3. -/

theorem bench_t3 : 1 < Nat.factorial 1 ∧ True := ⟨bench_t2, trivial⟩
