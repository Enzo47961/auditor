import Fixture.Dep
/-! Cenário 09 — o arquivo-alvo não executa nada; a dependência local executou ao ser compilada. -/

theorem uses : True := dep_true
