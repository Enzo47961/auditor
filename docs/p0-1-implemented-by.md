# P0-1 — `@[implemented_by]` gerado na elaboração (Fase 1, sub-fase 1a.1)

```
status: medição feita (auditor-measure, run 39845428621); 7,35 % das declarações do Mathlib caem só por ctorIdx gerado → L-34; política de TCB para gerado fica para a Fase 2
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

## 4. Medição no Mathlib inteiro

**Ferramentas:**
- `tools/phase1/ImplementedByScan.lean`: roda sob `lake env`, importa sem extensões (D-39);
- `tools/phase1/implemented_by_measure.py`.

**Passos:**
1. `dump`: toda constante do ambiente com `implemented_by`/`extern`.
2. `classify`:
   - nível TCB/usuário pela MESMA função do auditor (`tcb_boundary.classify`, Q7);
   - origem `source_written` (o fonte do módulo escreve `implemented_by X`, varredura léxica) ou gerada, separada por gerador.
3. `reach`: para cada declaração reportável do Mathlib (critério do inspetor), as categorias alcançáveis pelo mesmo percurso de dependências do inspetor.

**Conferência:** `tests/maintenance/test_phase1_tools.py` roda o pipeline inteiro no cenário 08 e exige que ele marque exatamente as declarações que o auditor marca.

**Execução:** `auditor-measure` no fork, [run 39845428621](https://github.com/Enzo47961/mathlib4/actions/runs/39845428621).
- Auditor `aa5750b`, fork `afd92f7`; nenhum `.lean` difere de `e1b2403b`.
- `dump` 3 s, `reach` 43 s, 7,5 GB de RSS. Isso não cabe na máquina do mantenedor (7 GB).
- Dados em `trabalho/p0/measure1/`.

### 4.1 Constantes com atributo de usuário: escrito × gerado

No ambiente do Mathlib há 2046 constantes com `implemented_by`/`extern`. 1721 são do toolchain (TCB pela Q7): 760 `implemented_by` e 961 `extern`. As de usuário:

| Categoria | Mathlib | Dependências | Gerador |
|---|---|---|---|
| `source_written` (escrito no fonte) | **0** | 20 (Aesop 11, Batteries 7, ProofWidgets 2) | autor |
| `generated_ctor_idx` | 186 | 74 (Aesop 42, Batteries 14, importGraph 7, ProofWidgets 5, Qq 4, LeanSearchClient 1, Plausible 1) | Lean, `mkCtorIdx` (`CtorIdx.lean:139`) |
| `generated_other` | 30 | 12 (Aesop 4, Batteries 4, Qq 2, Plausible 2) | Lean, termo `unsafe e` (`Lean/Elab/BuiltinNotation.lean:565`: `opaque …unsafe_impl_N` com `implemented_by`), em arquivos de meta-programação |
| `generated_type_name` | 0 | 3 (ProofWidgets) | Lean, `deriving TypeName` |
| `extern_user` | 0 | 0 | — |
| `boundary_unresolved` | 0 | 0 | — |

O Mathlib não escreve nenhum `implemented_by` no próprio fonte. Todo atributo de usuário dele é gerado pelo Lean. Nenhum gerado é de gerador do próprio projeto: o `compile_inductive%` não apareceu como categoria separada nesta medição.

### 4.2 Declarações do Mathlib que caem por atributo de usuário

Das **330 852** declarações reportáveis (critério do inspetor; inclui construtores, projeções e instâncias):

| Alcançam | Declarações | % |
|---|---|---|
| qualquer atributo de usuário | 24 374 | **7,367 %** |
| só atributos gerados | 24 360 | 7,363 % |
| **só `ctorIdx` gerado** | **24 322** | **7,351 %** |
| atributo escrito no fonte (dependências) | 14 | 0,004 % |
| termo `unsafe` gerado | 33 | 0,010 % |
| `deriving TypeName` | 5 | 0,002 % |

**Por área**, as que alcançam `ctorIdx` gerado: `CategoryTheory` 8448, `Algebra` 5083, `AlgebraicGeometry` 4720, `AlgebraicTopology` 1440, `Combinatorics` 682, `RepresentationTheory` 668, `Geometry` 598, `Tactic` 517, `Topology` 376 e outras. **Não é efeito da infraestrutura.** O grosso é teoria de categorias e o que depende dela: `cases`/`noConfusion` sobre tipos indexadores como `WalkingParallelPair`, `WalkingParallelPairHom` e `Pairwise.Hom`.

### 4.3 Conclusão e registro

- **> 5 % das declarações** caem só por atributo gerado. Pela instrução 24, isso vira **L-34**: a política de TCB para código gerado precisa de revisão na Fase 2.
- **Não há lacuna de integridade.** Todas essas declarações saem `implemented_by_candidate`, nunca `verified`.
- **A perda é de cobertura,** e concentrada em matemática.
- A proposta da seção 2 (reconhecer o `ctorIdx` pela forma) resgataria 24 322 declarações, 7,35 % do total. Fica para a Fase 2, com teste de equivalência (instrução 24).
