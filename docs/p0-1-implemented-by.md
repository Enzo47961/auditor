# P0-1 — `@[implemented_by]` gerado na elaboração (Fase 1, sub-fase 1a.1)

```
status: em andamento — mecanismo identificado no fonte e reproduzido; teste de regressão feito; medição no Mathlib inteiro preparada (workflow auditor-measure do fork), não executada
```

Classificação: `author-self-review` (L-26).

## 1. Mecanismo (fonte do Lean `v4.36.0-rc1`, commit `c9afcddf`)

| Gerador | Onde | O que gera |
|---|---|---|
| `mkCtorIdx` | `Lean/Meta/Constructions/CtorIdx.lean:77–141` | para todo indutivo com **≥ 2 construtores** que elimina em `Type`, não `unsafe` e fora dos tipos do runtime (`Nat`, `Int`…): `T.ctorIdx : T → Nat` (por `casesOn`) com **`@[implemented_by T.ctorIdx._impl]`** (linha 139). `_impl` é `unsafe` e vale `getObjTagNat x` (`Init/Prelude.lean:1382`). Com 1 construtor: `macroInline`, sem atributo |
| `noConfusionType` | `Lean/Meta/Constructions/NoConfusion.lean:103` (e `noConfusionEnum`, 367–418) | usa `T.ctorIdx`; por isso `cases`/injeção sobre igualdade de construtores chega a `ctorIdx` |
| `deriving DecidableEq` | `Lean/Elab/Deriving/DecEq.lean:113–154` | compara `ctorIdx` |
| `deriving TypeName` | `Lean/Elab/Deriving/TypeName.lean:25` | `unsafe def instImpl` + **`@[implemented_by instImpl] opaque inst`** (nomes higiênicos) |

O `ctorIdx` do PR #6 (`CategoryTheory.Limits.WalkingParallelPair.ctorIdx`) é o primeiro caso. O mecanismo exato, que a instrução 21 deixou "a confirmar", é `mkCtorIdx`, e não `deriving DecidableEq`.

## 2. Fronteira de TCB (decisão, regra da Q7)

- A Q7 decide a origem pelo `lake-manifest.json` e pelas raízes do toolchain, nunca pelo nome.
- O `ctorIdx` de um indutivo do Mathlib é uma constante **de um módulo do Mathlib**. Pela regra, o atributo é **de usuário**, embora o código que o gerou seja do toolchain.
- Decisão desta sub-fase: **manter assim**. Quem chega a um `ctorIdx` gerado sai `implemented_by_candidate` (L-5), nunca `verified`.
- Vale o mesmo para `deriving TypeName` e para geradores de projeto (por exemplo, `compile_inductive%` do Mathlib).

**Não há lacuna de integridade**, só de cobertura:
- A Etapa A não vê o atributo gerado (não está no texto), mas a Etapa B vê todo atributo do ambiente elaborado, gerado ou escrito.
- Nenhum `implemented_by` gerado chega a `verified` sem sinalização: demonstrado no cenário 08 e no teste de ponta a ponta da medição.
- A Etapa A não precisa ser estendida para os padrões de geração. Se fosse, ela só repetiria, pior (léxico), o que a Etapa B já faz no ambiente. Isso corresponde à opção (b) da instrução 24, com uma ressalva: a Etapa B **já é** a defesa. Isso está registrado aqui, não como limitação nova.

**Proposta (não aplicada; decisão do revisor).** Se a medição mostrar que o `ctorIdx` gerado derruba uma fração grande do Mathlib, existe um reconhecimento **estrutural** que não depende do nome:
- `T.ctorIdx` com `@[implemented_by T.ctorIdx._impl]`, em que `_impl` é `unsafe` e tem corpo exatamente `getObjTagNat` aplicado, uma constante de `Init`;
- e o corpo de `T.ctorIdx` é o `casesOn` que devolve o índice de cada construtor.

Com isso, a implementação é a do toolchain (TCB pela Q7) e a constante só embrulha. O scanner de medição já verifica a primeira metade dessa forma (`ctor_idx_shape`). Seria um relaxamento de política, com teste de equivalência no toolchain fixado. Fica para depois da medição.

## 3. Teste de regressão (cenário 08)

`tests/conformance/08-generated-implemented-by`. O arquivo não escreve `implemented_by`.

| Declaração | Chega a | Resultado exigido |
|---|---|---|
| `red_ne_green` (`cases` sobre `Color.red = Color.green`) | `Color.ctorIdx` (gerado) | `unresolved`, `implemented_by_candidate: [Color.ctorIdx]` |
| `idx_red` | `Color.ctorIdx` | idem |
| `instTypeNameTag`, `tag_name` | `inst._@…` de `deriving TypeName` | `unresolved`, `implemented_by_candidate` |
| `box_idx` (1 construtor), `plain`, `Color`, `Box` | nada com atributo | `verified` (a sinalização não é indiscriminada) |

Além disso, o teste exige que a Etapa A não veja nenhum `implemented_by` e que nenhuma declaração com candidato saia `verified`. `seg_injective` (`cases` sobre `Shape.seg a = Shape.seg b`) sai `verified`: o fecho dele não passa por `Shape.ctorIdx`. É um fato medido, não uma exigência do teste.

## 4. Medição no Mathlib inteiro (preparada, não executada)

- **Ferramentas:**
  - `tools/phase1/ImplementedByScan.lean`: roda sob `lake env`, importa sem extensões (D-39);
  - `tools/phase1/implemented_by_measure.py`.
- **Passos:**
  1. `dump`: toda constante do ambiente com `implemented_by`/`extern`, com módulo, `.olean`, faixa no fonte e forma do `ctorIdx`.
  2. `classify`:
     - nível TCB/usuário pela MESMA função do auditor (`tcb_boundary.classify`);
     - origem `source_written` (o fonte do módulo escreve `implemented_by X`, varredura léxica da Etapa A);
     - ou `generated_ctor_idx` / `generated_type_name` / `generated_other` (com a linha de origem);
     - mais `extern_user` e `boundary_unresolved`.
  3. `reach`: para cada declaração reportável do Mathlib (critério do inspetor), as categorias alcançáveis pelo mesmo percurso de dependências do inspetor, por busca no grafo reverso.
  4. `report`: tabela por categoria e pacote; declarações que alcançam cada categoria; declarações que alcançam **só** atributos gerados (as que caem só por geração); percentual das reportáveis.
- **Conferência:** `tests/maintenance/test_phase1_tools.py` roda o pipeline inteiro no cenário 08 e exige que ele marque exatamente as declarações que o auditor marca (`idx_red`, `instTypeNameTag`, `red_ne_green`, `tag_name`).
- **Execução:** o workflow `auditor-measure` do fork (dispatch, `measure: p0-1`). Localmente não cabe: importar o Mathlib inteiro excede a memória da máquina do mantenedor (7 GB).

Pendente: os números. Com eles, o critério de > 1 % das declarações (instrução 24) e a decisão sobre a proposta da seção 2.
