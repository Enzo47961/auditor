module

public import Mathlib.Data.Nat.Factorial.Basic
public import Mathlib.AuditorBenchmark.Chain.T1

@[expose] public section

/-! Benchmark 1b — `sorry` transitivo, elo T2. -/

theorem bench_t2 : 1 < Nat.factorial 1 := bench_t1 1
