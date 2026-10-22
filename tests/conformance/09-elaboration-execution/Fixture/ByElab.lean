import Lean
/-! Cenário 09 — `by_elab` executa código do usuário na elaboração (L-33). -/
open Lean in
theorem u : True := by_elab do
  (IO.FS.writeFile "marker_by_elab.txt" "executado" : IO Unit)
  return mkConst ``True.intro
