import Lean
/-! Cenário 09 — `run_tac` executa código do usuário na elaboração (L-33). Grava um marcador no
diretório de trabalho do build: a execução aconteceu antes da Etapa B. -/

theorem t : True := by
  run_tac do (IO.FS.writeFile "marker_run_tac.txt" "executado" : IO Unit)
  trivial

theorem t2 : 1 + 1 = 2 := rfl
