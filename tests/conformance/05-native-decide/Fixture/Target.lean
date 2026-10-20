/-! Cenário 05 — `native_decide` e a gramática estrita de justificativa:
`auditor_justified: reason="…" reviewer="@handle"` — uma linha, sem escape, exatamente uma. -/

-- (a) sem docstring
theorem nd_nodoc : 10 < 20 := by native_decide

/-- (b) docstring sem linha de justificativa. -/
theorem nd_plain_doc : 10 < 21 := by native_decide

/-- (c) justificativa válida.
auditor_justified: reason="kernel decide too slow" reviewer="@enzo" -/
theorem nd_justified : 10 < 22 := by native_decide

/-- (d) drift: justificativa na declaração vizinha, que NÃO usa native_decide.
auditor_justified: reason="drifted from neighbor" reviewer="@enzo" -/
theorem drift_holder : 1 = 1 := rfl
theorem drift_victim : 10 < 23 := by native_decide

/-- (e1) malformada: múltiplas linhas.
auditor_justified: reason="split
over lines" reviewer="@enzo" -/
theorem bad_multiline : 10 < 24 := by native_decide

/-- (e2) malformada: escape.
auditor_justified: reason="has \"quote\"" reviewer="@enzo" -/
theorem bad_escape : 10 < 25 := by native_decide

/-- (e3) malformada: sem reviewer.
auditor_justified: reason="no reviewer" -/
theorem bad_no_reviewer : 10 < 26 := by native_decide

/-- (e4) malformada: reviewer sem @.
auditor_justified: reason="bad handle" reviewer="enzo" -/
theorem bad_handle : 10 < 27 := by native_decide

/-- (e5) malformada: duas linhas de justificativa.
auditor_justified: reason="one" reviewer="@enzo"
auditor_justified: reason="two" reviewer="@enzo" -/
theorem bad_duplicate : 10 < 28 := by native_decide

-- (f) transitivo: consumidores sem native_decide próprio
theorem consumes_justified : 10 < 22 ∧ True := ⟨nd_justified, trivial⟩
theorem consumes_unjustified : 10 < 20 ∧ True := ⟨nd_nodoc, trivial⟩
