import Lake
open Lake DSL
package gen_allowlist
@[default_target] lean_exe dump where
  root := `Dump
  supportInterpreter := true
