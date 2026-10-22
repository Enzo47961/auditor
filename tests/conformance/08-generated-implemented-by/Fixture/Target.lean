/-!
Cenário 08 — `@[implemented_by]` gerado na elaboração (Fase 1, P0-1).

Nenhuma linha deste arquivo escreve `implemented_by`. O Lean gera `T.ctorIdx` para todo indutivo
com dois ou mais construtores que elimina em `Type`, com `@[implemented_by T.ctorIdx._impl]`
(`Lean/Meta/Constructions/CtorIdx.lean:139`, v4.36.0-rc1), e `noConfusionType` passa por ele
(`Lean/Meta/Constructions/NoConfusion.lean:103`). O módulo é do projeto, então pela Q7 o atributo
é de usuário: quem chega a `Color.ctorIdx` sai `implemented_by_candidate`, nunca `verified`.
-/

inductive Color where
  | red
  | green

/-- Chega a `Color.ctorIdx` pelo `noConfusion` de `cases`. -/
theorem red_ne_green : Color.red ≠ Color.green := by
  intro h
  cases h

/-- Chega a `Color.ctorIdx` diretamente. -/
theorem idx_red : Color.red.ctorIdx = 0 := rfl

/-- Indutivo com dois construtores e campos (não enumeração). -/
inductive Shape where
  | dot
  | seg (n : Nat)

theorem seg_injective (a b : Nat) (h : Shape.seg a = Shape.seg b) : a = b := by
  cases h
  rfl

/-- Um construtor só: `ctorIdx` sem `implemented_by` (`macroInline`). -/
structure Box where
  x : Nat

theorem box_idx (b : Box) : b.ctorIdx = 0 := rfl

/-- Não toca nenhum indutivo do arquivo. -/
theorem plain : (1 : Nat) + 1 = 2 := rfl

/-- `deriving TypeName` gera `@[implemented_by instImpl] opaque inst`
(`Lean/Elab/Deriving/TypeName.lean:25`). -/
structure Tag where
  n : Nat
deriving TypeName

theorem tag_name : TypeName.typeName Tag = TypeName.typeName Tag := rfl
