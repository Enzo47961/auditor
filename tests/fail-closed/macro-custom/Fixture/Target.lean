/-! Fail-closed — macro customizada declarada no arquivo-alvo.
A prova é aceita pelo kernel sem axiomas (GroundTruth.lean): sem a Etapa A, sairia
`Validada`. A sintaxe nova é invisível para a varredura léxica → deve ser fail-closed. -/

macro "obviously" : tactic => `(tactic| rfl)

theorem two_plus_two : 2 + 2 = 4 := by obviously
