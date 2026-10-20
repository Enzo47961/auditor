import Fixture.Target
-- O kernel prova a negação de e_bad sem axiomas; juntos, derivam False.
theorem e_bad_is_false : myF 2 3 ≠ 5 := by decide
theorem boom : False := e_bad_is_false e_bad
theorem e_mixed_is_false : myF 2 3 + 1 ≠ 6 := by decide
theorem boom_c : False := e_mixed_is_false e_mixed
#print axioms e_bad
#print axioms e_mixed
#print axioms e_mixed_is_false
#print axioms e_bad_is_false
#print axioms e_zero
#print axioms h_zero
