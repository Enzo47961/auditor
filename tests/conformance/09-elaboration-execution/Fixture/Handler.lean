import Lean
/-! Cenário 09 — por ambiente (L-33a): um handler de tática registrado por atributo é código que o
elaborador executa quando a sintaxe aparece. O tipo `Tactic` alcança `IO.RealWorld`. -/
open Lean Elab Tactic in
@[tactic Lean.Parser.Tactic.tacticRfl] def myRfl : Tactic := fun _ => do
  (IO.FS.writeFile "marker_handler.txt" "executado" : IO Unit)
  throwUnsupportedSyntax

theorem h : True := trivial
