import Lean
/-! Cenário 11 — L-33 (b): código executado no build do alvo tenta adulterar o auditor. O caminho
vem de `AUDITOR_TAMPER_TARGET` (definido pelo teste: o pacote do auditor copiado, ou o binário do
inspetor num cache temporário). Sem a variável, o `run_tac` não faz nada além de existir. -/

theorem t : True := by
  run_tac do
    if let some p ← (IO.getEnv "AUDITOR_TAMPER_TARGET" : IO (Option String)) then
      let h ← IO.FS.Handle.mk p .append
      h.putStr "\n# adulterado\n"
  trivial
