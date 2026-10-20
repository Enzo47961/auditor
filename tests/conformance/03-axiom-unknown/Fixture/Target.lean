import Fixture.Dep
/-! Cenário 03 — arquivo-alvo usa o axioma desconhecido declarado na dependência. -/

theorem usa_axioma : (0 : Nat) = 1 := minhaAxioma

/-- Controle: no mesmo arquivo, sem o axioma. -/
theorem nao_usa : (0 : Nat) = 0 := rfl
