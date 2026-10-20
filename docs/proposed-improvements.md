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

## Q7 — RESOLVIDA: opção (a), com especificação de fronteira

Implementações do toolchain são TCB. A fronteira é declarada pelo toolchain (raízes de biblioteca em `<sysroot>/lib/lean`) e pelo `lake-manifest.json` (raízes de usuário), não pelo nome do módulo. Algoritmo, garantias e manutenção estão em `docs/tcb.md`, seção "Fronteira de TCB"; testes unitários em `tests/tcb`. O canário é o cenário `06-tcb-boundary`, e o `04b-extern` ganhou o caso (c).

**Mudança no inspetor (v2).** O inspetor deixou de decidir `in_toolchain`. Agora emite só fatos: o caminho real do `.olean` de cada módulo, o sysroot, o search path efetivo e as docstrings de todas as donas. A decisão TCB/usuário fica no Python, testável sem Lean.

## D-1 a D-3 — ACEITAS

- **D-1, com a adição do revisor.** `#reduce` passou a ser fail-closed, como `#eval`; antes **não estava coberto** (caía em `allowed`). Aplicando o mesmo critério ("avalia → fail-closed"), verifiquei no fonte do toolchain que `#guard` e `#widget` chamam `evalExpr`, a mesma execução de código compilado do `#eval`; os dois também passaram a fail-closed. `classification_version` subiu para 2. Testes: `tests/stage_a/test_stage_a.py::test_risky_commands`.
- **D-2** e **D-3:** sem mudança.

## Q8. Comandos que só reduzem (não bloqueia nada)

Pelo critério de D-1, `#reduce` (redução) foi equiparado a `#eval` (execução). Outros comandos do core também reduzem termos sem executar código compilado: `#guard_expr` (com `=~`, defeq), `#check_simp` (roda `simp`), `#synth` (resolução de instâncias), `#check_tactic` (roda uma tática). Eles continuam `allowed`. Pergunta: o critério do revisor é "executa código" (então só `#reduce` é exceção explícita) ou "avalia/reduz" (então os quatro também viram fail-closed)? Sem resposta, mantenho `allowed`. Mudar é uma linha em `classification.toml`.

## D-4 a D-10 — detalhes completos para revisão

Nenhuma é urgente para a Policy: a Policy foi implementada sem depender de veto a elas. Se alguma for vetada, a mudança é local.

### D-4. Pino da allow-list de projeto
- **O que faz.** `env_pin = SHA-256(versão do pino ‖ lean-toolchain ‖ bytes do lake-manifest.json)`, com cada parte prefixada pelo comprimento (`src/auditor/allowlist.py::env_pin`). A allow-list de projeto guarda esse valor. A Etapa A recalcula o pino a partir do ambiente atual e só usa a allow-list se os valores baterem.
- **O que muda no comportamento.** Qualquer mudança no toolchain ou em qualquer byte do manifest (versão de dependência, até espaço em branco) torna a allow-list obsoleta: `allowlist_stale`, a Etapa A não usa a lista e o relatório sai com exit 2. O **fonte do próprio projeto não entra** no pino. Se entrasse, a allow-list do Mathlib ficaria obsoleta a cada commit, e na prática seria regenerada em cada auditoria, que é a allow-list dinâmica rejeitada na Q5(b). Consequência registrada em L-16: um comando novo do projeto cai em `unknown_command` (fail-closed); um comando redefinido mantém a classificação antiga.
- **Como testa.** `tests/allowlist/test_project_allowlist.py`: pino igual ao recalculado; manifest alterado em um byte, campo `toolchain`, campo `env_pin` ou campo `kind` adulterados → `allowlist_stale`; `--check` detecta a deriva. Fim a fim: `tests/cli/test_cli.py::test_stale_project_allowlist_is_infra` (exit 2, nenhuma `verified`). Mutações: retirar a comparação do pino e retirar o manifest do hash são detectadas.

### D-5. Classificação de comandos de projeto
- **O que faz.** O gerador separa os comandos extraídos em comandos do core (classificados por `tools/gen_allowlist/classification.toml`) e comandos novos do projeto. Os novos só saem de `unclassified` se estiverem em `<projeto>/.auditor/classification.toml`. O gerador recusa (exit 2) classificação que: cite comando inexistente; cite comando do core (um projeto não pode reclassificar `#eval` como permitido); classifique um comando duas vezes; ou tenha chave desconhecida.
- **O que muda no comportamento.** Comando de projeto não classificado → `unclassified_command` em qualquer posição → declarações `Não resolvida`. No core, o padrão para comando sem risco listado é `allowed`, porque o critério foi aplicado a todos os 122 comandos extraídos. No projeto, o padrão é fail-closed, porque ninguém olhou os comandos novos.
- **Como testa.** `tests/allowlist`: `my_lemma` sem classificação → `unclassified_command`; com classificação → aceito; os quatro tipos de classificação inválida → exit 2. Mutações: tornar `unclassified` vazio, desligar a checagem de comando obsoleto, de duplicata e de chave desconhecida são detectadas.

### D-6. Módulos do projeto na extração
- **O que faz.** O gerador roda `lake build` no projeto e importa **todos** os `.olean` em `<projeto>/.lake/build/lib/lean`, mais `Lean`. Os comandos extraídos são os de todo esse ambiente.
- **O que muda no comportamento.** A allow-list cobre todo comando disponível em qualquer arquivo do projeto, e não só nos arquivos que importam tudo. Um comando definido num módulo que o alvo não importa fica na allow-list, mas não pode aparecer no alvo sem import (o Lean não o reconheceria), então o efeito é nulo. Projeto sem build → erro explícito.
- **Como testa.** `tests/allowlist`: o comando `my_lemma`, definido em `Mini.Cmd`, aparece na allow-list gerada; projeto sem `lake-manifest.json` → exit 2.

### D-7. Execução do inspetor
- **O que faz.** `Inspect.lean` é compilado como executável com o toolchain do projeto-alvo, numa pasta de cache fora do repositório. A chave do cache é o hash do fonte + toolchain + lakefile do inspetor. O executável roda sob `lake env` na raiz do projeto, para herdar o `LEAN_PATH` fixado.
- **O que muda no comportamento.** A primeira auditoria com um toolchain novo leva cerca de 15 s a mais (compilação); as seguintes reutilizam o binário. Qualquer mudança no fonte gera binário novo, e `source_sha256` e `binary_sha256` entram na TCB e no fingerprint. Falha de compilação → `inspector_build_failed` (exit 2).
- **Como testa.** `tests/stage_b`: a identidade do inspetor depende do toolchain; o `source_sha256` do relatório é o hash do fonte; a versão declarada em Lean e em Python coincidem. Evidência adicional: a saída do executável compilado é **idêntica, byte a byte,** à do interpretador (`lean --run`) no fixture 05.

### D-8. Declarações reportadas
- **O que faz.** O relatório cobre as constantes do módulo-alvo que (a) têm faixa de declaração no fonte (`declRangeExt`) e (b) têm nome de usuário. Nomes privados são julgados pela parte de usuário. Ficam fora: `match_N`, `_proof_N`, recursores, `noConfusion`, equações.
- **O que muda no comportamento.** Entram também constantes geradas com faixa no fonte: construtor e projeções de `structure`, instâncias anônimas (`instInhabitedP`) e o parser criado por `macro` (`tacticObviously`). Cada uma recebe estados próprios. Declarações `private` são reportadas com o nome interno (`_private.Mod.0.hidden`); o vínculo com a Etapa A (`set_option … in`) usa o nome de usuário.
- **Como testa.** `tests/stage_b::test_reported_declarations_exact` (conjunto exato por fixture, incluindo `edges` e `macro`); `test_edges_internal_names_never_reported`; `test_edges_private_declaration_reported_and_owned`. Mutações: retirar o filtro de faixa e o tratamento de privadas são detectadas.

### D-9. Formato do toolchain
- **O que faz.** Para conferir que o inspetor rodou com o Lean fixado, o wrapper extrai a versão de `leanprover/lean4:vX.Y.Z` (com `-rcN` opcional) e a compara com `Lean.versionString` emitido pelo inspetor.
- **O que muda no comportamento.** Toolchains em outro formato (`nightly-…`, forks, `stable`) → `toolchain_unrecognized`, exit 2, sem tentar auditar. Divergência de versão → `toolchain_mismatch`, exit 2.
- **Como testa.** `tests/stage_b::test_unrecognized_toolchain_format` e `test_ingest_file_level_mismatch`. A mutação que retira a checagem de versão é detectada.

### D-10. Fim de linha
- **O que faz.** `.gitattributes` com `* -text` desliga a conversão automática de fim de linha do git. Os geradores gravam bytes UTF-8 com LF, e o `--check` compara bytes, não texto.
- **O que muda no comportamento.** No Windows, sem isso, o checkout converteria o `lake-manifest.json` para CRLF: o `env_pin` mudaria e toda allow-list de projeto pareceria obsoleta. Os hashes da TCB (fonte do inspetor, política) também mudariam entre sistemas.
- **Como testa.** Indiretamente: `tests/maintenance/test_allowlist_fresh.py` compara bytes e passou nos dois sistemas (Linux e Windows), e os testes do pino dependem dos bytes exatos.

## Decisões locais da Policy, Schema e CLI (para veto)

- **D-11. `debug.skipKernelTC true` é `set_option` proibido.** A opção faz o Lean aceitar declarações **sem** checagem do kernel; é o caso extremo de "set_option que relaxa checagem". Teste: `tests/policy/test_rules.py::test_forbidden_option_rejects`.
- **D-12. Allow-list de opções.** Reconhecidas: `maxHeartbeats`, `maxRecDepth`, `synthInstance.maxHeartbeats`, `synthInstance.maxSize`, `autoImplicit`, `relaxedAutoImplicit`, `checkBinderAnnotations`, e os prefixos `linter.`, `pp.`, `trace.`, mais `profiler`. Opção fora da lista → `Não resolvida`, `set_option_unrecognized`. É provável que o Mathlib use opções fora dela; a lista será ajustada com evidência da camada 2.
- **D-13. Alcance de `set_option` em nível de arquivo ou seção.** Atinge toda declaração que não esteja comprovadamente **antes** da opção. O fim de seção não é rastreado (aproximação conservadora: mais declarações atingidas, nunca menos). Forma `in` que não se vincula a declaração com nome, sendo a opção proibida ou não reconhecida → `set_option_unattributed` em todas as declarações. Teste fim a fim: `tests/policy/set-option`.
- **D-14. Declaração vista pela Etapa A e ausente do ambiente** → entrada própria no relatório, `Não resolvida`/`Não resolvido`, razão `declaration_not_found_in_environment`, exit 1.
- **D-15. Arquivo sem declarações** → `no_declarations`, exit 1 (sem nada a selar, nunca exit 0). O schema impõe que exit 0 tenha pelo menos uma declaração.
- **D-16. Entrada não reconhecida pela Etapa A** (sintaxe nova, comando fora da allow-list, Unicode proibido) afeta só `proof_status` (`Não resolvida`, `stage_a_unrecognized`). As premissas vêm do ambiente elaborado, que a Etapa B analisou por completo.
- **D-17. Precedência dentro de cada estado:** pior efeito vence (`Rejeitada` > `Não resolvida` > `Validada`; `Não conforme` > `Não resolvido` > `Conforme`). É a mesma regra da Q4, aplicada dentro de cada estado: `sorry` + candidato `implemented_by` → `Rejeitada`.
- **D-18. `declaration_hash`** = SHA-256 de (nome, tipo de declaração, `Expr.hash` do tipo, `Expr.hash` do valor). Determinístico; o `Expr.hash` subjacente é estrutural de 64 bits (L-14). É `null` para declaração não elaborada.
- **D-19. Layout do relatório.** A spec lista `tcb` e `execution_metadata` como campos por declaração; eles estão em cada declaração (cópia) **e** no nível do relatório. Também há campos de arquivo (`compilation`, `infrastructure`, `file_findings`, `not_covered`, `exit_code`). O schema amarra `overall_status` à tabela da Q4, `correspondence_status` à constante `Não auditada`, `Validada` à TCB completa e exit 0 à ausência de entradas não reconhecidas.
- **D-20. Dependência `jsonschema` (≥ 4.18)** em tempo de execução. A CLI valida todo relatório antes de gravá-lo; relatório fora do schema → `report_schema_invalid`, exit 2.
- **D-21. Timeout padrão de 300 s** (o orçamento de 5 min da spec), configurável com `--timeout`; `--timeout-test artificial` marca o relatório (L-11).

## Correções feitas na retomada (sessão no Windows)

- O código da Etapa B e da Q5 da sessão anterior não foi preservado: só o `stage_a.py` (já com suporte a allow-list de projeto) e os documentos. A Q5 e a Etapa B foram reimplementadas a partir das decisões registradas.
- Portabilidade: a saída do Lean passou a ser decodificada como UTF-8 explicitamente (no Windows, o padrão é cp1252, o que quebrava dois testes de ground truth com nomes Unicode).
