module

public import Mathlib.Data.Nat.Factorial.Basic
public import Mathlib.AuditorBenchmark.Chain.T3

@[expose] public section

/-! Benchmark 1b — `sorry` transitivo, elo T4. -/

theorem bench_t4 : 1 < Nat.factorial 1 := bench_t3.1
