/-
Cenário 07 — cabeçalho do sistema de módulos (v4.36), como em todo arquivo do Mathlib:
`module` antes de `public import` (D-57), e metavariáveis sintéticas `?_` na prova (D-56).
-/
module

public import Fixture.Base

/-! Nenhum dos dois pode, sozinho, deixar uma declaração `Não resolvida`. -/

/-- Prova legítima com `refine ⟨?_, ?_⟩`. -/
public theorem both : baseVal = 2 ∧ 1 + 1 = 2 := by
  refine ⟨?_, ?_⟩
  · rfl
  · rfl

/-- Controle: `sorry` continua detectado com o cabeçalho `module`. -/
public theorem bad : 1 = 2 := by sorry
