/-! Cenário 04 — `@[implemented_by]`.
(a) atributo sozinho, sem avaliação nativa no caminho do kernel → candidato.
(b) atributo alcançado por `native_decide` com justificativa válida → padrão combinado.
    Ground truth: a implementação mente, e `GroundTruth.lean` deriva `False`. -/

def gImpl (n : Nat) : Nat := n
/-- (a) -/
@[implemented_by gImpl] def g (n : Nat) : Nat := n
theorem g_zero : g 0 = 0 := rfl

def fImpl (_ : Nat) : Bool := true
@[implemented_by fImpl] def f (_ : Nat) : Bool := false

/-- (b) Justificativa válida para `native_decide`; não cobre `implemented_by`.
auditor_justified: reason="scenario 04 combined pattern" reviewer="@fixture" -/
theorem f_bad : f 0 = true := by native_decide
