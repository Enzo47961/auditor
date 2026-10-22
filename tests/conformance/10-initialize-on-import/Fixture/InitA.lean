/-! Cenário 10 (ground truth, P0-2 b / L-33) — `initialize` no próprio arquivo. A instrução 24 pede
confirmar no toolchain fixado: (1) não executa na elaboração deste arquivo; (2) executa quando o
arquivo é importado (`Lean/Compiler/InitAttr.lean`, `runInitAttrForMod`). -/

initialize
  IO.FS.writeFile "marker_initialize.txt" "executado"

theorem a : True := trivial
