module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I04: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

unsafe def benchUnsafe : ℕ := 0

theorem bench_inc_I04 : 1 + 1 = 2 := rfl
