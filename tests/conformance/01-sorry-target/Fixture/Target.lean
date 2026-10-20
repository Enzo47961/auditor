/-! Cenário 01 — `sorry` no arquivo-alvo. -/

/-- Enunciado FALSO admitido com `sorry`. Ground truth: `GroundTruth.lean` prova `¬ (1 = 2)`. -/
theorem foo : 1 = 2 := by sorry

/-- Controle: prova legítima no mesmo arquivo, sem axiomas. -/
theorem ok : 1 + 1 = 2 := rfl
