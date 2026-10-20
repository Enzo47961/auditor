import Fixture.B
/-! Fail-closed — sintaxe válida, mas A importa B e B importa A. -/

theorem a_thm : True := trivial
