/-! Arestas do inspetor (Etapa B). Cada caso exercita um caminho do fecho de
dependências ou da resolução da declaração dona. Ground truth: `#print axioms`. -/

-- axioma alcançado só pelo TIPO de um construtor (inductInfo → ctors → ctorInfo.type)
axiom secret : Nat
inductive I where
  | mk : secret = secret → I
theorem uses_I : Nonempty I := ⟨I.mk rfl⟩

-- declaração privada com sorry, consumida por uma pública
private theorem hidden : 1 = 2 := sorry
theorem uses_hidden : 1 = 2 := hidden

-- native_decide dentro de um auxiliar `where`: dona é `outer.aux`, não `outer`
theorem outer : 10 < 20 := aux
where aux : 10 < 20 := by native_decide

-- `match` gera auxiliar interno (`m.match_1`), que não deve ser reportado
def m : Nat → Nat
  | 0 => 1
  | _ => 2

-- estrutura: projeções e construtor gerados
structure P where
  x : Nat

-- instância anônima: nome gerado pelo elaborador
instance : Inhabited P := ⟨⟨0⟩⟩

-- `partial def`: o compilador gera `@[implemented_by loop._unsafe_rec]`
partial def loop (n : Nat) : Nat := if n = 0 then 0 else loop (n - 1)

-- axioma declarado no próprio alvo, e uma declaração que o usa
axiom local_ax : (0 : Nat) = 1
theorem uses_local : (0 : Nat) = 1 := local_ax
