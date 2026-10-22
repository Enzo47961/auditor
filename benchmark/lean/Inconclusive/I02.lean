module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I02: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

set_option backward.isDefEq.respectTransparency false in
theorem bench_inc_I02 : 2 + 2 = 4 := rfl
