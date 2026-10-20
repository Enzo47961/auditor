import Fixture.B
/-! Cenário 02 — arquivo-alvo. Cadeia A → B → C → D (3 imports); o `sorry` está em D. -/

/-- Depende transitivamente de `d_lemma` (sorry). -/
theorem a_main : 2 + 2 = 5 := b_lemma

/-- Controle: no mesmo arquivo, não depende da cadeia. -/
theorem a_clean : True := trivial
