import Fixture.Target
-- Não auditado. Verifica os fixtures com o próprio Lean, independentemente do auditor.
theorem foo_is_false : ¬ (1 = 2) := by decide
#print axioms foo
#print axioms ok
