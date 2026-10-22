/-! Cenário 09 — por ambiente (L-33a): `@[extern]` liga a constante a um símbolo nativo, que o
interpretador chama se a constante for avaliada na elaboração. -/
@[extern "lean_nat_add"] opaque myAdd : Nat → Nat → Nat

theorem e : True := trivial
