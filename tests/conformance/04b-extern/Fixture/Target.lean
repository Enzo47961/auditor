import Fixture.Dep
/-! Cenário 04b — `@[extern]` (O-5), análogo ao cenário 04.
(a) atributo sozinho, sem avaliação nativa no caminho do kernel → candidato.
(b) `@[extern]` alcançado por `native_decide` com justificativa válida → padrão combinado.
    Ground truth: o código nativo mente, e `GroundTruth.lean` deriva `False`. -/

/-- (a) atributo na própria declaração do alvo. -/
@[extern "lean_nat_sub"] def h (a b : Nat) : Nat := a + b
/-- (a) depende de `h` sem avaliação nativa. -/
theorem h_zero : h 0 0 = 0 := rfl
/-- (a) depende de `myF` (dependência) sem avaliação nativa. -/
theorem e_zero : myF 0 0 = 0 := rfl

/-- (b) Justificativa válida para `native_decide`; não cobre `extern`.
auditor_justified: reason="scenario 04b combined pattern" reviewer="@fixture" -/
theorem e_bad : myF 2 3 = 5 := by native_decide
