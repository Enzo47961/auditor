# P0-2 — Taxa de fail-closed da Etapa A (Fase 1, sub-fase 1a.2)

```
status: em andamento — (a) feito; kill criterion atingido (L-30); (b) aguarda a L-33a (feita) e a remedição oficial; (c) remedido depois de (a)
```

Classificação: `author-self-review` (L-26). Nenhum número deste documento é alegação de cobertura do Mathlib a terceiros.

## 1. Método

- **Ferramenta:** `tools/phase1/stage_a_causes.py`. Roda a mesma `stage_a.analyze` do CI, com a allow-list de projeto do fork, nos `--top` primeiros arquivos do ranking de `tools/layer2/fanout.py`, e classifica cada item não reconhecido em uma de quatro causas:
  - **(a)** falso positivo: `unknown_command`;
  - **(b)** comando não sintático: `metaprogramming_command` ou `unclassified_command`;
  - **(c)** sintaxe: `syntax_extension_declared`;
  - **(d)** outra causa.
- **Entrada:** fork `auditor-base` `018d7db`, que é o Mathlib `e1b2403b` mais `.github/` e `.auditor/` (allow-list com 259 comandos, `author-self-review`). Ranking de fanout com procedência `e1b2403b`, SHA-256 do manifesto `f77f47db…`, `leanprover/lean4:v4.36.0-rc1`.
- **Populações:**
  - os 60 arquivos de maior fanout (o gate do revisor);
  - **adicionalmente**, os 8651 arquivos da biblioteca `Mathlib`. A medição extra não substitui o gate; a seção 4 explica por que ela importa.
- Execução local (Windows), determinística para o mesmo checkout e a mesma allow-list. Dados brutos em `trabalho/p0/` (`causes60*.json`, `causes_all*.json`).

## 2. Resultados

| População | Antes (Etapa A v2) | Depois de (a) (Etapa A v3) |
|---|---|---|
| Top-60 por fanout | 41/60 fail-closed (**68,3 %**) | 39/60 (**65,0 %**) |
| Biblioteca `Mathlib` inteira | 1333/8651 (**15,4 %**) | 1244/8651 (**14,4 %**) |

Distribuição de causas no top-60. Um arquivo pode ter mais de uma causa; a coluna "só esta" conta os arquivos que a correção daquela causa resgataria sozinha.

| Causa | Antes: arquivos | Antes: só esta | Depois de (a): arquivos | Depois de (a): só esta |
|---|---|---|---|---|
| (a) falso positivo | 3 | 1 | 0 | 0 |
| (b) não sintático | 21 | 7 | 21 | 7 |
| (c) sintaxe | 32 | 17 | 32 | 18 |
| (d) outra | 2 | 1 | 0 | 0 |

Depois de (a), os 39 arquivos do top-60 que falham se dividem assim: 18 só por sintaxe, 7 só por comando não sintático e 14 pelas duas causas.

- **Comandos não sintáticos no top-60** (arquivos): `initialize` 15, `register_option` 5, `run_cmd` 3, `with_weak_namespace` 2, `register_linter_set` 1, `register_simp_attr` 1, `register_label_attr` 1, `declare_core_config_elab` 1, `simproc_decl` 1.
- **Sintaxe no top-60** (arquivos): `syntax` 21, `elab` 7, `macro` 6, `prefix`, `elab_rules`, `infixl`, `infixr`, `notation`, `macro_rules` 4 cada, `declare_syntax_cat` e `notation3` 2 cada, `binder_predicate`, `infix` e `postfix` 1 cada.
- **Mathlib inteiro, depois de (a)** (arquivos com a causa / só com ela):
  - (a) falso positivo: 44 / 29;
  - (b) não sintático: 230 / 120;
  - (c) sintaxe: 1090 / 969;
  - (d) outra: 8 / 2.

  A sintaxe dominante é `notation` (553 arquivos), seguida de `syntax` (163), `infixl` (123), `notation3` (111) e `elab` (102).

## 3. (a) Falsos positivos: o que mudou (Etapa A versão 3)

A Etapa A tratava como início de comando todo token na coluna 0. Medido no Mathlib inteiro antes da correção: 167 arquivos com `unknown_command`, 112 deles só por isso. As causas eram quatro:

1. **Termo continuado na coluna 0.** Exemplos: `{ … with }`, `(…)`, `⟨…⟩`, `match`, `let`, `fun`, `f!"…"`, `do`, `for`.
   - Esses tokens entraram em `continuation` (`tools/gen_allowlist/classification.toml`).
   - Também entraram as palavras de termo da lista do revisor que **não** são comandos: `have`, `show`, `from`, `by`, `if`, `then`, `else`, `calc`, `s!`, `m!`.
   - Da lista do revisor, `end`, `section`, `namespace`, `open`, `variable` e `universe` **não** entraram: são comandos de verdade e já são aceitos como comandos. Pô-los em `continuation` seria errado, e a guarda abaixo recusaria.
2. **`add_decl_doc` depois de docstring.** A sintaxe é `docComment >> "add_decl_doc " >> ident` (`Lean/Parser/Command.lean:939`). O token inicial é a docstring, então `add_decl_doc` na coluna 0 é o segundo token do comando. A nova lista `doc_continuation` o aceita **só** logo depois de uma docstring `/--`. Esse caso explicava 82 arquivos.
3. **`cmd%` na coluna 0** (por exemplo, `compile_inductive%`). A checagem da coluna 0 usava a chave sem o `%`. O arquivo continua fail-closed, mas agora pela classificação certa (`metaprogramming_command`), não como `unknown_command`.
4. **Palavra de declaração fora de posição de declaração.** Produzia `declaration_name_unresolved` em quatro padrões, nenhum dos quais começa uma declaração:
   - `.abbrev`, `.opaque` e `.structure`: construtor ou campo;
   - `` `lemma ``: literal de nome;
   - `(lemma := …)`: argumento nomeado;
   - `[class]` e `@[class, …]`: o atributo `class`.

**Guardas.** Uma continuação nunca pode ser token inicial de comando:
- `check_continuations` (`src/auditor/allowlist.py`) faz o gerador do core e o de projeto recusarem (exit 2) uma continuação que seja comando no ambiente;
- em tempo de execução, a Etapa A descarta qualquer continuação que o projeto tenha como comando.

Conferido no toolchain fixado e na allow-list do Mathlib: nenhuma colisão.

Detecção de risco não muda: comando de risco continua detectado em qualquer posição, inclusive depois de uma continuação (teste `test_continuation_does_not_hide_risky_commands`).

**Resíduo de (a), mantido fail-closed de propósito:**
- identificadores soltos na coluna 0 (`Eq.symm`, `rfl`, `X`…): não há regra léxica segura que os diferencie de um comando desconhecido;
- itens de `@[…]` que quebram linha (`deprecated`, `+typeChanged`);
- palavras de declaração dentro de quotations (`def $id …`), em arquivos que já declaram sintaxe;
- JSX do ProofWidgets (`<span class=…>`).

No Mathlib inteiro sobram 44 arquivos com falso positivo, 29 só com ele.

**Testes:** 9 testes novos (22 casos) em `tests/stage_a`. **Mutações:** 10 novas no grupo `stage_a`, 23/23 detectadas localmente (a oficial é o `auditor-mutation` do fork, depois do envio).

## 4. Teto do que (b) pode resgatar, e o kill criterion

No top-60, 32 arquivos declaram sintaxe. A instrução 24 mantém sintaxe genuína fail-closed. Logo:
- relaxando **todos** os comandos não sintáticos, inclusive `run_cmd`, o melhor caso é 28 limpos e 32/60 = **53,3 %** de fail-closed;
- sem relaxar `run_cmd` (2 arquivos dos 7 que falham só por não sintáticos: `Mathlib/Init.lean` e `Mathlib/Basic/FunLike/Basic.lean`), o melhor caso é 34/60 = **56,7 %**.

**Portanto, o kill criterion de P0-2 (> 50 % depois de (a) e (b)) já está atingido**, seja qual for a leitura de (b). Pela instrução 24: a Fase 1 continua, mas a alegação de "cobertura do Mathlib" fica bloqueada até a Fase 2. A meta de < 30 % é inalcançável nessa população sem relaxar sintaxe.

**Observação sobre a população (não muda o gate).**
- O top-60 por fanout é, em grande parte, infraestrutura: 36 dos 60 estão em `Tactic/`, `Lean/` ou `Util/`, e 25 desses 36 falham. Esses arquivos declaram sintaxe por função.
- Fora dessas pastas, 14 dos 24 falham. São arquivos `Defs`/`Notation`/`Logic`, quase todos por `notation`/`infix`.
- No Mathlib inteiro, a taxa é 14,4 %. A causa dominante é `notation` (553 arquivos).
- `notation`/`infix` geram macros que rodam na elaboração. Pela L-17 elas são fail-closed, mas o código é **gerado pelo toolchain**, como o `ctorIdx` do P0-1.
- Relaxá-las mudaria a política de sintaxe: é decisão do revisor, não desta sub-fase.

## 5. (b) Comandos não sintáticos: leitura iniciada e PARADA

Leitura no commit fixado, até aqui:

| Comando | Leitura | Situação |
|---|---|---|
| `run_cmd` | executa código | **mantido fail-closed** (instrução 24) |
| `initialize` | `Lean/Compiler/InitAttr.lean`: procedimentos `[init]` "são rodados nos arquivos que IMPORTAM o arquivo onde estão definidos"; `runInitAttrForMod` percorre só os módulos importados. Não executa na elaboração do próprio arquivo | candidato a `allowed` pelo critério da L-17; **não aplicado** (ver abaixo) |
| `register_option`, `register_simp_attr`, `register_label_attr`, `register_linter_set` | expandem para `initialize` (a confirmar caso a caso no fonte) | pendente |
| `simproc_decl` | declara um simproc que um `simp` posterior do MESMO arquivo executa | provavelmente fica fail-closed; pendente |
| `with_weak_namespace`, `declare_core_config_elab` | pendente | pendente |

**Por que parei.** A leitura de (b) depende do critério da L-17: um comando é fail-closed se pode executar código na elaboração, antes da Etapa B. Ao testar esse critério, encontrei uma contradição na arquitetura da Fase 0 (`limitations.md`, L-33). A Etapa A **não detecta** `run_tac` (tática) nem `by_elab` (termo), e os dois executam código do usuário na elaboração do próprio arquivo, inclusive IO.
- Demonstrado num projeto descartável: os dois gravaram um arquivo-marcador durante o `lake build`.
- O auditor completo deu `verified` e exit 0 nos dois arquivos.

A L-17 cobre só comandos. A defesa contra execução pré-auditoria, que é o que justifica tratar `initialize` e os demais com cuidado, tem um caminho aberto por tática e termo. Relaxar comandos com base nessa defesa antes de decidir o que fazer com o caminho aberto seria a ordem errada. A decisão é do revisor (instrução 24, "quando parar e perguntar": contradição da Fase 0 exposta pela Fase 1).

## 6. Pendências

- Decisão do revisor sobre o achado da seção 5 (L-33).
- Retomar (b) caso a caso, com teste de ausência de efeito para cada relaxamento.
- Remedir (c) no fork, com a medição oficial no GitHub Actions.
- ~~L-30~~ registrada (instrução 24): 65,0 % depois de (a); teto 53,3 %; cobertura do Mathlib bloqueada até a Fase 2.

## 7. Resposta do revisor (instrução 24) e sequência confirmada

- **Kill criterion atingido é resultado correto.** Registrado como L-30, sem maquiar o número. A taxa de 14,4 % da biblioteca inteira fica registrada à parte. A causa dominante (`notation` gerada pelo toolchain) vira pergunta para a Fase 2.
- **L-33 (pergunta 1), opção (c) aprovada:**
  - o (a) foi aplicado (L-33a, `docs/l33-inventory.md`);
  - o (b), hash do inspetor e do auditor, é item da Fase 1.
- **Sequência de (b) do P0-2 (pergunta 2), confirmada:**
  - retomar só depois da L-33a;
  - `register_option`, `register_*_attr` e `register_linter_set` pela mesma leitura de `initialize`;
  - `run_cmd` e `simproc_decl` mantidos fail-closed.
- **Exigência do revisor sobre `initialize`, confirmada por execução (cenário 10):**
  - (1) não executa na elaboração do próprio arquivo;
  - (2) executa quando o arquivo é importado.

  Logo, `initialize` em dependência é vetor de execução. A Etapa A não vê a dependência, e o cruzamento léxico da L-33a só cobre `run_tac`/`by_elab`.
  - **Decisão:** `initialize` **não** é reclassificado como `allowed`, nem no alvo. No alvo, a L-33a por ambiente já o marca (o procedimento é uma constante `IO …`).
  - Relaxá-lo só faz sentido depois da mitigação (b) ou de uma extensão do cruzamento de dependências para código registrado.
  - O mesmo vale para `register_option`, `register_*_attr` e `register_linter_set`, que expandem para `initialize`.
  - O teto de (b) no top-60 cai, portanto, para os arquivos que falham só por `simproc_decl`/`run_cmd`/`with_weak_namespace`/`declare_core_config_elab`, todos mantidos fail-closed ou ainda por ler. Resultado: **(b) não resgata nenhum arquivo do top-60 nesta fase.**
