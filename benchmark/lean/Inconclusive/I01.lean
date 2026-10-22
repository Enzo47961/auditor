module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I01: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

macro "bench_m01" : term => `(2)

theorem bench_inc_I01 : bench_m01 = 2 := rfl
