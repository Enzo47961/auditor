import Fixture.Target
-- Não auditado. Verifica os fixtures com o próprio Lean, independentemente do auditor.
theorem bad_is_false : ¬ (1 = 2) := by decide
#print axioms both
#print axioms bad
