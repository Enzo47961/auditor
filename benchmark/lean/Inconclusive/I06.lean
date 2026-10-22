module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I06: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

syntax "bench_s06" : term
macro_rules | `(bench_s06) => `(1)

theorem bench_inc_I06 : bench_s06 = 1 := rfl
