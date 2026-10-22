module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — inconclusivo I03: a prova é correta; o arquivo usa o que a Etapa A ou a
política não reconhecem. Esperado: Não resolvida, nunca verified. -/

notation "𝔹𝟘" => (0 : ℕ)

theorem bench_inc_I03 : 𝔹𝟘 + 1 = 1 := rfl
