import Fixture.Target
-- O kernel prova a negação de f_bad sem axiomas; juntos, derivam False.
theorem f_bad_is_false : f 0 ≠ true := by decide
theorem boom : False := f_bad_is_false f_bad
#print axioms f_bad
#print axioms f_bad_is_false
#print axioms g_zero
