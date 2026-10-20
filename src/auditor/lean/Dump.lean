import Lean
open Lean Parser

/-! Extrator da allow-list da Etapa A: imprime os tokens iniciais da categoria `command`
do parser, um por linha, no ambiente `Lean` + módulos opcionais.

Uso: `lean --run Dump.lean [arquivo-com-módulos]` (um nome de módulo por linha).
Sem argumento: só `Lean` (allow-list do core). Lê o ambiente; não aplica classificação. -/

def main (args : List String) : IO UInt32 := do
  initSearchPath (← findSysroot)
  let mods ← match args with
    | [] => pure #[]
    | [f] => pure ((← IO.FS.lines f).filter (·.trim ≠ "") |>.map (·.trim.toName))
    | _ => throw <| IO.userError "uso: Dump.lean [arquivo-com-módulos]"
  let env ← importModules (#[{module := `Lean}] ++ mods.map ({module := ·})) {} (loadExts := true)
  let st := parserExtension.getState env
  let some cat := st.categories.find? `command | throw <| IO.userError "no command category"
  let toks := cat.tables.leadingTable.toList.map (·.1.toString) |>.eraseDups
  for t in toks.toArray.qsort (· < ·) do IO.println t
  IO.eprintln s!"leadingParsers (sem token inicial): {cat.tables.leadingParsers.length}"
  return 0
