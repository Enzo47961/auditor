/-! Projeto limpo para os testes do auditor-ci: duas declarações que o auditor verifica
(nenhum axioma, nenhuma avaliação nativa), independentes da decisão da Q9. -/

theorem add_kernel : Nat.add 2 3 = 5 := rfl

theorem two_le_three : 2 ≤ 3 := by decide
