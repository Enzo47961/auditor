import Lean
/-! Cenário 09 — dependência local com `run_tac`, importada por `Uses.lean`. -/

theorem dep_true : True := by
  run_tac do (IO.FS.writeFile "marker_dep.txt" "executado" : IO Unit)
  trivial
