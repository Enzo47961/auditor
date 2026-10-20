/-! Cenário 06 — fronteira de TCB (Q7, opção a). Canário.
`Nat.add` é `@[extern]` do próprio toolchain (`Init.Prelude`). Implementações do toolchain
são TCB e não disparam as regras de `@[extern]`/`@[implemented_by]`. Se o Lean mudar onde
`Nat.add` vive, ou a fronteira declarada pelo manifest/toolchain, este cenário acusa. -/

/-- Avaliação nativa que passa por `Nat.add`, com justificativa válida.
auditor_justified: reason="scenario 06 tcb boundary" reviewer="@fixture" -/
theorem add_native : 2 + 3 = 5 := by native_decide

/-- `Nat.add` sem avaliação nativa: só o kernel. -/
theorem add_kernel : Nat.add 2 3 = 5 := rfl
