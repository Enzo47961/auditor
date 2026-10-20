import Lean
open Lean Parser
def main : IO Unit := do
  initSearchPath (← findSysroot)
  let env ← importModules #[{module := `Lean}] {} (loadExts := true)
  let st := parserExtension.getState env
  let some cat := st.categories.find? `command | throw <| IO.userError "no command category"
  let toks := cat.tables.leadingTable.toList.map (·.1.toString) |>.eraseDups
  for t in toks.toArray.qsort (· < ·) do IO.println t
  IO.eprintln s!"leadingParsers (sem token inicial): {cat.tables.leadingParsers.length}"
