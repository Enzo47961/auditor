# Objeções registradas à especificação

Registradas **antes** da implementação. Mudanças requerem autorização explícita.

## O-1. Justificativa de `native_decide` — RESOLVIDA: opção (B)

**Decisão:** docstring com a gramática estrita, sem escape, sem múltiplas linhas; qualquer desvio é violação. O cenário 05 inclui o drift multi-declaração. A opção (C) fica registrada como fallback em `limitations.md` (L-4), condicionada a uma objeção real do Mathlib, sem migração preventiva.

**Problema.** O atributo `@[auditor_justified]` (item 3) só existe se for registrado num módulo importado. O Mathlib não vai depender do pacote do auditor, então o mecanismo decidido é inaplicável ao alvo principal. A classificação inicial desta objeção como "não substantiva" estava errada.

### Investigação (toolchain `leanprover/lean4:v4.22.0`, commit `ba2cbbf0`)

**(A) Atributo ignorado silenciosamente sem o pacote: NÃO FUNCIONA.**

```
A.lean:2:2: error: unknown attribute [auditor_justified]
A2.lean:2:21: error: unexpected identifier; expected prio     ← forma com argumentos
```

Atributo não registrado é erro de elaboração, e a forma com argumentos nem passa pelo parser. Não há mecanismo de atributo "opcional".

**(B) Docstrings no ambiente elaborado: FUNCIONA.**

Projeto lake com `Fix/Target.lean` compilado para `.olean`. Inspetor separado importa o módulo via `importModules` e lê com `findDocString?`, sem acesso ao texto-fonte:

```
justified   | doc=some "Lema sobre ordem.\nauditor_justified: reason=\"kernel decide too slow\" reviewer=\"@enzo\" "
unjustified | doc=some "Docstring comum, sem justificativa. "
nodoc       | doc=none
```

Atribuição do `native_decide` à declaração dona, por nome:

```
referência direta a Lean.ofReduceBool: justified._proof_1_3, unjustified._proof_1_3, nodoc._proof_1_3
'consumer' depends on axioms: [Lean.ofReduceBool]   ← consumer usa justified; herda transitivamente
```

Algoritmo: para cada declaração auditada, encontrar no seu fecho de dependências as constantes que referenciam `Lean.ofReduceBool`/`Lean.ofReduceNat` diretamente. Para cada uma, resolver a declaração dona removendo os componentes internos do nome (`justified._proof_1_3` → `justified`) e exigir justificativa na docstring da dona. No exemplo, `consumer` fica coberto porque a única fonte é `justified`, que está justificada. Se alguma dona não estiver justificada, a violação é atribuída a ela e propagada às dependentes.

### Avaliação de (B) contra as três objeções do item 3

- **(a) "Comentários não existem no ambiente elaborado".** Docstrings existem: ficam no `.olean` e a Etapa B os lê diretamente. A Etapa A não participa.
- **(b) "Cruzamento por posição quebra em refatoração".** Não há cruzamento por posição: a docstring pertence à declaração pelo nome, no ambiente.
- **(c) "Docstring na declaração errada e ninguém detecta".** Detecta-se: se a justificativa estiver em outra declaração, a dona do `native_decide` fica sem ela, e o resultado é violação (fail-closed).

### Riscos residuais de (B)

1. **A convenção de nomes auxiliares (`X._proof_N`) é detalhe de implementação do compilador** e pode mudar entre versões do Lean. Mitigação: se a resolução da dona não encontrar uma declaração não-interna, o resultado é `Não resolvida` com razão `native_decide_owner_unresolved`. A convenção entra no teste de defasagem de `docs/maintenance.md`.
2. **A docstring aparece na documentação gerada do Mathlib.** Não sei se revisores do Mathlib aceitam uma linha estruturada visível em docs. Não testável aqui.
3. **Falsificação.** Qualquer autor pode escrever a linha. O atributo tinha a mesma propriedade; a aprovação continua humana e fora do escopo.
4. **Gramática estrita.** Linha `auditor_justified: reason="…" reviewer="@handle"` com parse estrito. Linha malformada é violação, não é ignorada.

### Recomendação

Adotar (B). Ele responde às três objeções do item 3 com evidência, funciona sem dependência no projeto-alvo e é fail-closed por construção. Como reverte uma decisão explícita (item 3 rejeitou docstrings), **aguardo autorização**. Se (B) for rejeitado, apresento os trade-offs de (C).

Fixtures da investigação: preservados para virar testes de regressão da regra.

## O-2. Isenção de `maxHeartbeats 0` depende da Etapa A

`set_option` não é registrado no ambiente elaborado; a condição (b) só pode ser cruzada sintaticamente. Mitigação: só a forma `set_option maxHeartbeats 0 in <declaração>` é elegível à isenção (o `in` vincula a opção à declaração seguinte, sem cruzamento por posição). A forma em nível de arquivo ou seção nunca é isentável.

## O-3. `maxHeartbeats 0` como `Rejeitada` — RESOLVIDA

Implementado como decidido: `Rejeitada`, razão `set_option_violation`, apenas na declaração que usa a opção. Uma declaração dependente é avaliada pelos próprios méritos (opção i) e pode ser `Validada` + `Conforme`; a dependência aparece no campo `depends_on_rejected: [nomes]` do schema v1.

## O-4. Warnings não têm campo no schema da spec

O item 5 introduz warnings (confusables). Campo opcional `warnings` (lista) por declaração e no nível do relatório. É aditivo e não altera campos obrigatórios.

## Q1–Q3 — RESOLVIDAS

- **Q1:** (X) ortogonal estrito, mais `overall_status` (`verified` só se ambos os estados forem positivos). Aplicado em todos os testes.
- **Q2:** o cenário 03 foi reescopado para axioma desconhecido (`03-axiom-unknown`): `Não resolvido` + `unknown_axiom`.
- **Q3(a):** `g_zero` → `Não resolvida`, `implemented_by_candidate`.
- **Q3(b):** justificativa órfã → violação `orphan_justification`.

### Registros sobre a aplicação (para veto)

- **R-1. A cobertura descrita na Q2 não bate com (X).** A Q2 descreve o cenário 02 como "proibido em dependência, via sorryAx". Pela tabela (X), o `sorryAx` afeta só `proof_status`, e as premissas são avaliadas sem ele: o 02 testa admissão transitiva, não a categoria "proibido" nas premissas. Essa categoria fica coberta pelo 05 (`Lean.ofReduceBool` sem justificativa → `Não conforme`). Um axioma proibido que não seja `sorryAx` nem `ofReduceBool` só terá cobertura nos testes de regressão da policy. Implementei a tabela literalmente.
- **R-2. `orphan_justification` vai para `proof_status: Rejeitada`.** Derivação: a spec define `Rejeitada` como "violação concreta de política demonstrada", e (X) reserva `premises_status` para dependências.

## Q4–Q6 — RESOLVIDAS

- **Q4:** precedência `rejected` > `unresolved` > `verified` ("pior estado vence"). Formalizada como tabela no README; entra no schema v1 na etapa de Schema.
- **Q5:** allow-list de projeto gerada por `auditor-gen-allowlist --project <dir>`, vinculada ao pino do ambiente; allow-list obsoleta é fail-closed. Testes da camada 1 contra um projeto Lake mínimo (`tests/allowlist`). A allow-list do Mathlib é evidência da camada 2. A correção semântica da allow-list é Fase 1+ (L-16).
- **Q6:** alvo que não compila → exit 1, `proof_status: Não resolvida`, `overall_status: unresolved`, razão `compile_failure`.

## Decisões locais tomadas na Etapa A (para veto)

- **D-1. Classificação de risco dos comandos** (`tools/gen_allowlist/classification.toml`). Fail-closed quando o comando introduz sintaxe, executa código arbitrário capaz de alterar o ambiente, é interno do core ou oculta conteúdo (`#exit`). `#eval` e `run_cmd` são fail-closed; `unif_hint`, `grind_pattern` e `#check` são permitidos.
- **D-2. Regra de confusables:** detecção por pares (TR39 §4) no arquivo, ignorando componentes de um caractere (L-6). Avisar sobre todo caractere confusable dispararia em quase todo arquivo do Mathlib (α→a, ι→i, ℝ→R).
- **D-3. Estrutura:** cenários como diretórios-projeto; pacote em `src/auditor/` (layout Python padrão), não em `src/main.py`.

## O-5. `@[extern]` — ACEITO
Entra na spec com a mesma categoria de risco de `@[implemented_by]`. Cenário `04b-extern` criado, com o mesmo formato de ground truth do 04: (a) atributo sozinho; (b) combinado com `Lean.ofReduceBool`. O ground truth deriva `False`: um `@[extern "lean_nat_add"]` de usuário sobre uma definição que multiplica. O fixture precisa de `precompileModules := true`, porque o interpretador só avalia um `extern` de usuário se o módulo que o define tiver código nativo carregado. As regras de política para `extern` dependem de Q7.

## Q7. Implementações nativas do próprio toolchain (SUBSTANTIVA; bloqueia a Policy)

**Problema.** As regras decididas são: `@[implemented_by]` no fecho de dependências → candidato (item 2, Q3a), e `@[extern]` → mesma categoria (O-5). Aplicadas ao pé da letra, contradizem decisões já aprovadas, porque o **próprio toolchain** usa esses atributos no caminho de quase tudo. Evidência do inspetor no toolchain fixado:

| Declaração | Atributos do toolchain no fecho |
|---|---|
| `nd_justified : 10 < 22 := by native_decide` (05c, aprovado como `verified`) | `@[extern]`: `Nat.ble`, `Nat.decLt`, `Nat.decLe`, `Nat.add` |
| `foo : 1 = 2 := by sorry` (01) | `@[implemented_by]`: `Lean.Name.str`, `Lean.Name.num`, `Lean.Name.anonymous` |
| `e_bad` (04b) | `@[extern]`: `Nat.beq`, `Nat.decEq`, `Nat.mul`, `Nat.add`, e `myF` (do usuário) |

Consequências da leitura literal:
1. **Todo `native_decide` sobre `Nat` vira `Rejeitada`** (`extern_reaches_native_eval`), inclusive o 05c justificado. Isso anula a decisão O-1/B: justificar `native_decide` deixaria de ter efeito.
2. Grande parte do Mathlib vira `Não resolvida`, porque `Array`, `Name`, `String` etc. do core têm `@[implemented_by]`.

**Opções.**
- **(a) Implementações do toolchain são TCB.** Atributos em constantes cujo `.olean` está sob `<sysroot>/lib/lean` não disparam as regras; as demais disparam. O compilador e o runtime já estão na TCB enumerada (L-1), e a justificativa de `native_decide` já é, por definição, a aceitação explícita de confiar neles. A distinção é feita pelo caminho do `.olean`, não pelo prefixo do nome do módulo (que um projeto poderia imitar). O inspetor já emite `in_toolchain`.
- **(b) Allow-list explícita** em `policy.toml` das implementações confiáveis do toolchain, gerada mecanicamente e versionada por toolchain (como a allow-list de comandos). Mais granular; custa manutenção a cada subida do toolchain.
- **(c) Leitura literal.** `native_decide` fica, na prática, sempre rejeitado na Fase 0; o 05c e a opção B de O-1 precisam ser revistos.

**Recomendação: (a).** É a única que preserva as decisões já tomadas (05c `verified`, O-1/B) sem lista nova para manter, e mantém o cenário 04/04b intacto: o risco demonstrado (implementação mentirosa) vem de código **fora** do toolchain. O custo: um bug no runtime do Lean fica fora do alcance, mas ele já estava (L-1). **Não implementei nenhuma das opções.** A Etapa B emite o fato bruto (`in_toolchain`), e a Policy aguarda a decisão.

Efeito colateral a medir na camada 2: `@[implemented_by]` do **próprio Mathlib** (fora do toolchain) torna dependentes `Não resolvida` em qualquer das opções. A magnitude só aparece nas medições.

## Decisões locais tomadas na Q5 e na Etapa B (para veto)

- **D-4. Pino da allow-list de projeto** = SHA-256 de (`lean-toolchain`, bytes do `lake-manifest.json`). Não inclui o fonte do próprio projeto: incluí-lo invalidaria a allow-list a cada commit e a tornaria, na prática, dinâmica (contrário à Q5). Consequência registrada em L-16.
- **D-5. Classificação de projeto.** Comando novo do projeto sem classificação → `unclassified` (fail-closed), ao contrário do core, onde todo comando extraído passou pelo critério. A classificação de projeto não pode reclassificar comandos do core nem citar comandos inexistentes ou duplicados; o gerador recusa (exit 2).
- **D-6. Módulos do projeto** para a extração: todos os `.olean` produzidos pelo `lake build` do projeto (`.lake/build/lib/lean`).
- **D-7. Execução do inspetor.** Compilado por (hash do fonte, toolchain) e guardado em cache fora do repositório; executado sob `lake env` no projeto-alvo. A saída do executável é byte a byte idêntica à do interpretador (`lean --run`), verificado no fixture 05.
- **D-8. Declarações reportadas** = constantes do módulo-alvo com faixa de declaração e nome de usuário, privadas incluídas (L-15). Consequência: `macro` gera uma constante reportada (`tacticObviously`).
- **D-9. Formato do toolchain.** Só `leanprover/lean4:vX.Y.Z` (com `-rcN` opcional) é reconhecido para conferir a versão do inspetor; outros formatos (ex.: `nightly-…`) são fail-closed (`toolchain_unrecognized`).
- **D-10. Fim de linha.** O repositório desliga a conversão de fim de linha do git (`.gitattributes`: `* -text`), porque o pino e os hashes dependem dos bytes exatos (no Windows, o checkout com CRLF mudaria o `env_pin`). Os geradores gravam LF explicitamente.

## Correções feitas na retomada (sessão no Windows)

- O código da Etapa B e da Q5 da sessão anterior não foi preservado: só o `stage_a.py` (já com suporte a allow-list de projeto) e os documentos. A Q5 e a Etapa B foram reimplementadas a partir das decisões registradas.
- Portabilidade: a saída do Lean passou a ser decodificada como UTF-8 explicitamente (no Windows, o padrão é cp1252, o que quebrava dois testes de ground truth com nomes Unicode).
