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

## Q4–Q6. Decisões abertas surgidas na Etapa A (nenhuma bloqueia a Etapa A)

### Q4. Precedência do `overall_status` em estados mistos
"rejected se qualquer negativo" e "unresolved se qualquer Não resolvido" se aplicam ao mesmo tempo quando uma declaração tem um estado negativo e outro não resolvido (ex.: `sorry` + axioma desconhecido). Nenhum fixture atual cai nesse caso. Opções: (a) `rejected` prevalece, porque há evidência concreta de problema; (b) `unresolved` prevalece. Inclinação: (a). Bloqueia a etapa de Schema.

### Q5. Allow-list de comandos do Mathlib (SUBSTANTIVA para a camada 2)
A allow-list atual é só do core. Comandos do Mathlib (`lemma`, `alias`, `assert_not_exists`, `library_note`, …) resultam em `unknown_command`, e então **todo arquivo do Mathlib sai `Não resolvida`**. As medições da camada 2 rodariam, mas sem produzir nenhum selo. Opções:
(a) allow-list do Mathlib gerada pelo mesmo extrator contra o commit fixado do Mathlib, versionada por commit e regenerada no procedimento de manutenção. Exige build do Mathlib, então é gerada no fork (camada 2). Subir o commit sem regenerar resulta em fail-closed;
(b) allow-list dinâmica, extraída do ambiente do alvo em tempo de auditoria. Isso deixa de ser "versionada", contrariando a decisão 6.
Inclinação: (a). A classificação de risco dos comandos do Mathlib também é manual, e é trabalho de revisão real (o Mathlib tem dezenas de comandos próprios).

### Q6. Exit code para falha de compilação do alvo
A spec dá exit 2 para "input inválido, timeout, ambiente inconsistente" e exit 1 para "qualquer falha". Um arquivo que não compila (incluindo ciclo de imports) poderia ser qualquer dos dois. Os testes fail-closed atuais exigem só exit ≠ 0. Inclinação: exit 2, porque sem elaboração não há declaração auditável. Bloqueia a etapa de CLI.

## Decisões locais tomadas na Etapa A (para veto)

- **D-1. Classificação de risco dos comandos** (`tools/gen_allowlist/classification.toml`). Fail-closed quando o comando introduz sintaxe, executa código arbitrário capaz de alterar o ambiente, é interno do core ou oculta conteúdo (`#exit`). `#eval` e `run_cmd` são fail-closed; `unif_hint`, `grind_pattern` e `#check` são permitidos.
- **D-2. Regra de confusables:** detecção por pares (TR39 §4) no arquivo, ignorando componentes de um caractere (L-6). Avisar sobre todo caractere confusable dispararia em quase todo arquivo do Mathlib (α→a, ι→i, ℝ→R).
- **D-3. Estrutura:** cenários como diretórios-projeto; pacote em `src/auditor/` (layout Python padrão), não em `src/main.py`.

## O-5. `@[extern]` (observação, não implementada)
Ver L-13. Adicionar a regra seria expandir escopo; fica registrada para a spec.
