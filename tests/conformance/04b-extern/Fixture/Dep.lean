/-! Cenário 04b — dependência com `@[extern]` que mente.
Kernel: multiplicação. Código nativo: `lean_nat_add` (soma), símbolo real do runtime. -/
@[extern "lean_nat_add"] def myF (a b : Nat) : Nat := a * b
