module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I05: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

theorem bench_inc_I05 : 3 = 3 :=
rfl
