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

## Q8. Comandos que só reduzem — RESOLVIDA (ver "Rodada da instrução 10"; pergunta original abaixo)

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
- **D-15 (REVISADA pelo revisor: exit 2, `no_declarations_found`, `--allow-empty`; texto original:)** Arquivo sem declarações → `no_declarations`, exit 1 (sem nada a selar, nunca exit 0). O schema impõe que exit 0 tenha pelo menos uma declaração.
- **D-16. Entrada não reconhecida pela Etapa A** (sintaxe nova, comando fora da allow-list, Unicode proibido) afeta só `proof_status` (`Não resolvida`, `stage_a_unrecognized`). As premissas vêm do ambiente elaborado, que a Etapa B analisou por completo.
- **D-17. Precedência dentro de cada estado:** pior efeito vence (`Rejeitada` > `Não resolvida` > `Validada`; `Não conforme` > `Não resolvido` > `Conforme`). É a mesma regra da Q4, aplicada dentro de cada estado: `sorry` + candidato `implemented_by` → `Rejeitada`.
- **D-18. `declaration_hash`** = SHA-256 de (nome, tipo de declaração, `Expr.hash` do tipo, `Expr.hash` do valor). Determinístico; o `Expr.hash` subjacente é estrutural de 64 bits (L-14). É `null` para declaração não elaborada.
- **D-19. Layout do relatório.** A spec lista `tcb` e `execution_metadata` como campos por declaração; eles estão em cada declaração (cópia) **e** no nível do relatório. Também há campos de arquivo (`compilation`, `infrastructure`, `file_findings`, `not_covered`, `exit_code`). O schema amarra `overall_status` à tabela da Q4, `correspondence_status` à constante `Não auditada`, `Validada` à TCB completa e exit 0 à ausência de entradas não reconhecidas.
- **D-20. Dependência `jsonschema` (≥ 4.18)** em tempo de execução. A CLI valida todo relatório antes de gravá-lo; relatório fora do schema → `report_schema_invalid`, exit 2.
- **D-21. Timeout padrão de 300 s** (o orçamento de 5 min da spec), configurável com `--timeout`; `--timeout-test artificial` marca o relatório (L-11). **Revisada na instrução 11:** 90 s por arquivo (`--timeout-file`).

## Rodada da instrução 10 — resoluções

- **Q8 — RESOLVIDA** com o critério do revisor: fail-closed se o comando *pode executar código compilado em tempo de elaboração, antes que a Etapa B possa inspecionar o ambiente*. `#guard_expr`, `#check_tactic` → fail-closed; `#check`, `#synth`, `#check_simp` → permitidos (revisados). O critério e a tabela estão em `limitations.md` (L-17); `classification_version = "3"`.
- **D-15 — REVISADA** conforme o revisor: arquivo sem declarações → exit 2, `no_declarations_found`. `--allow-empty` torna explícito o caso de arquivo só de imports (exit 0, aviso `empty_file_allowed`, `execution_metadata.allow_empty: true`). O schema impõe que exit 0 sem declarações exige `allow_empty: true`.
- **Aceitas:** D-4 a D-13 e D-20.
  - D-7: a taxa de acerto do cache é medida na Action (`docs/ci.md`).
  - D-8: as exclusões estão em L-15.
  - D-20: `jsonschema` e seu fecho transitivo entram na TCB (`tcb.aggregator.python_dependencies`, com versões exatas); dependência não resolvível → TCB incompleta.
- **Teste anti-LLM transitivo:** percorre o mesmo fecho da TCB (`src/auditor/pydeps.py`); uma dependência nova, mesmo transitiva, que traga biblioteca de LLM o faz falhar (testado com um grafo sintético de dois níveis).
- **Testes de mutação versionados:** `tools/mutation/` + `docs/maintenance.md`, com teste de integridade do catálogo.

## Decisões locais do CI (para veto)

- **D-22. Falha do job.** Arquivo com exit 1 (rejeição ou não resolução) faz o job falhar; só infraestrutura (orçamento, timeout, exit 2) deixa o job verde com o label `auditor-failed-infra`. Se o check do job bloqueia merge é configuração do repositório-alvo (branch protection), não da ferramenta.
- **D-23. `auditor-tier1.yml` é reutilizável** (`workflow_call`), com modelos de chamada em `ci/templates/`. Neste repositório ele não roda em `pull_request`: os fixtures são, de propósito, rejeitados, e auditá-los aqui só produziria jobs vermelhos sem significado. O CI do próprio auditor é `ci.yml` (a suíte inteira).
- **D-24. Separação de privilégios em três workflows.** O job que roda código do PR tem só leitura. O label vem de `workflow_run` (sem checkout, artefato tratado como não confiável). O comentário vem de `issue_comment` (sem checkout, só OWNER/MEMBER/COLLABORATOR). Alternativa rejeitada: `pull_request_target` com checkout do PR, que daria token de escrita a código não confiável. Testado como política em `tests/ci/test_workflows.py`.
- **D-25. Fixação de versões** (**revisada na instrução 11**: SHA obrigatório; ver D-35). Instalador do elan fixado em `v4.2.4`. Ações oficiais do GitHub fixadas por tag de versão maior (`@v4`, `@v5`), não por SHA; o teste aceita os dois formatos. Para o fork, recomendo fixar por SHA (mudança só nos modelos).
- **D-26. `#check_tactic_failure`** foi classificado como fail-closed por derivação direta do critério da Q8 (roda tática do usuário, como `#check_tactic`).
- **D-27. Subprocesso do `auditor-ci`.** Cada arquivo é auditado em processo separado (`python -m auditor check`), com o mesmo pacote que orquestra (caminho do pacote no `PYTHONPATH`). O isolamento impede que um arquivo afete o seguinte; o timeout do subprocesso é o restante do orçamento + 30 s.
- **D-28. O que o orçamento de 5 min mede** (**revisada na instrução 11**: inclui a preparação). O orçamento cobre a auditoria (todos os arquivos, incluindo o `lake build` de cada módulo-alvo). Instalação do elan, do Python e `lake exe cache get` ficam fora dele: são preparação do runner, medidas pela duração total do job. Se o revisor entender que os 5 min da spec incluem a preparação, o ajuste é passar o tempo já gasto no job para o `auditor-ci` descontar do orçamento.

## Rodada da instrução 11 — resoluções

- **Aceitas sem modificação:** D-14, D-16, D-17, D-19, D-20, D-22, D-23, D-24, D-26, D-27.
- **D-18 — ACEITA para a Fase 0**, com L-14. Item de Fase 1 em `docs/roadmap.md`: substituir o hash estrutural de 64 bits por SHA-256 truncado a 128 bits ou BLAKE3-128 (64 bits não resiste a colisão adversarial: quem forja uma colisão troca uma declaração sem mudar o hash).
- **D-21 — REVISADA:** timeout **por arquivo** de 90 s (`--timeout-file`, na CLI e no `auditor-ci`); o orçamento de 5 min é wall-clock do PR; arquivo que estoura o timeout encerra a auditoria do PR com exit 2. O default será reajustado pelo p95 medido na camada 2 (`tools/layer2/timings.py`).
- **D-25 — REVISADA, obrigatória:** toda action fixada por SHA de commit, neste repositório e nos modelos; procedimento de atualização em `docs/maintenance.md`. Ao aplicar, apareceu um erro na D-25 original (D-35).
- **D-28 — REVISADA:** o orçamento é wall-clock do PR, do trigger ao relatório, **incluindo `lake exe cache get`**. 5 min é o SLA do steady-state; cache `cold` → orçamento estendido (15 min), `first_run: true`, `cache_cold_extension` e label `auditor-first-run` quando passa dos 5 min. Os PRs de medição da camada 2 são feitos depois do primeiro run.
- **README, "Status":** "Fase 0 = Camada 1 (done) + Camada 2 (pending user evidence)"; a Fase 1 depende da camada 2.

## Decisões locais da instrução 11 (para veto)

- **D-29. Exit 2 do PR e cor do job.** `auditor-ci run` sai com o exit code do PR (0/1/2). Infraestrutura vence: rejeição + timeout → exit 2. A cor do job continua a da D-22: o passo da auditoria aceita 0/1/2, e um passo dedicado falha o job só quando `audit_failed` é verdadeiro. Exit 2 sozinho → job verde + `auditor-failed-infra` (critério 3 da spec: não bloqueia merge).
- **D-30. Origem do relógio.** Primeira tentativa: `github.event.pull_request.updated_at` (o evento do PR; inclui a fila do runner). Re-execução (`run_attempt > 1`): início do job, senão uma re-execução nasceria com o orçamento esgotado. O `outcome.json` declara `clock_origin` (`trigger`, `job_start`, ou `auditor_start`/`auditor_start_fallback` fora do GitHub ou com carimbo inválido).
- **D-31. Como `cache_state` é medido.** Dois sinais: restauração do cache de build do alvo (`hit`/`partial`/`miss`/`none`) e presença do binário do inspetor. `cold` = algum sinal frio; `delta` = cache de build parcial; `warm` = o resto. O orçamento estendido só é concedido com evidência positiva de cache frio. `first_run` é `cache_state == cold`: inclui cache despejado (o GitHub remove caches sem uso há 7 dias), não só o primeiro run literal no fork.
- **D-32. Cache do Mathlib no job.** `~/.cache/mathlib` (onde `lake exe cache get` guarda os arquivos) é restaurado com `actions/cache/restore`, chave por SO + `lean-toolchain` + commit base, `restore-keys` pelo prefixo (`partial`), e salvo quando não houve acerto exato. O tamanho desse diretório diante do limite de cache do repositório é verificação da camada 2.
- **D-33. Labels.** `auditor-failed-infra` vence `auditor-first-run`: cache cold que estoura o orçamento estendido é infraestrutura. `auditor-first-run` só quando `cache_cold_extension` (cold, sem infraestrutura, total > 5 min). O workflow de label aceita só esses dois nomes.
- **D-34. Inspetor compilado antes do primeiro arquivo.** Com o binário fora do cache, o `auditor-ci` o compila antes de auditar: o custo entra no orçamento do PR, não no timeout de 90 s de um arquivo.
- **D-35. Correção da D-25 original: o elan não estava fixado.** O `elan-init.sh` tirado da tag `v4.2.4` baixa a release **`latest`** do elan (`releases/latest/download/...`). O relatório anterior dizia "elan fixado em v4.2.4", o que só era verdade para o script. Agora os workflows baixam `elan-x86_64-unknown-linux-gnu.tar.gz` da release `v4.2.4` e conferem o SHA-256 antes de executar. Resíduos (L-18): o toolchain Lean baixado pelo elan e as dependências Python instaladas pelo pip não são conferidos por hash no CI.
- **D-36. `--timeout` continua aceito** como sinônimo de `--timeout-file` na CLI (mesmo destino; o default é 90 s). **Rejeitada na instrução 12** (ver lá).
- **D-37. `outcome.json` passou a `auditor-ci-outcome/2`.** O `label-decision` rejeita a versão anterior (resulta em `auditor-failed-infra`, fail-closed).
- **D-38. Fanout para escolher o arquivo da medição.** `tools/layer2/fanout.py`: fanout = número de módulos do projeto que importam o módulo, direta ou transitivamente, a partir do cabeçalho de imports. Nome de import ilegível (ex.: com `«»`) é erro, não é ignorado.

## Rodada da instrução 12 — resoluções

- **Aceitas:** D-29, D-30, D-31, D-32, D-33, D-34, D-35, D-37.
- **L-18 → roadmap (Fase 1):** toolchain Lean e dependências Python verificados por hash (`docs/roadmap.md`).
- **D-36 — REJEITADA e aplicada:** `auditor check --timeout` foi removido (sem sinônimo). Os nomes "total" foram para o orçamento do PR no `auditor-ci`: `--budget` → `--timeout-total`, `--first-run-budget` → `--timeout-total-first-run`; entradas do workflow `budget-seconds` → `timeout-total-seconds`, `first-run-budget-seconds` → `timeout-total-first-run-seconds`. O timeout por arquivo continua `--timeout-file` (D-21 aceita). Registrado em `CHANGELOG.md`. **Interpretação a confirmar:** a instrução diz "renomeie `--timeout` para `--timeout-total`". Na CLI `auditor check`, que audita um arquivo, `--timeout` era o timeout por arquivo, que já se chama `--timeout-file`. Renomeá-lo para `--timeout-total` desfaria a D-21. Por isso o nome "total" foi aplicado ao que de fato é total: o orçamento do PR. Se a intenção era outra, a troca é mecânica.
- **D-38 — detalhes:** `docs/ci.md`, "Escolha do arquivo de maior fanout (D-38)": (a) algoritmo, (b) justificativa e alternativas, (c) testes. Rodado no Mathlib real (commit `e1b2403b`, 8651 módulos, sem erro de cabeçalho). Foi acrescentado o fecho direto (`imports_transitive`), porque o custo da auditoria de um arquivo cresce com ele, e não com o fanout.
- **Bloqueio da camada 2 — opção (X) executada:** toolchain do auditor `v4.22.0` → **`v4.36.0-rc1`** (o do Mathlib `master`, commit `e1b2403b`, em 2026-10-20). Allow-list regenerada, inspetor portado, fixtures recompilados, suíte inteira rodada. Procedimento em `docs/maintenance.md`, "Procedimento ao subir o toolchain". Dois achados mudam significado (D-39, D-43) e um muda a fronteira (D-42).
- **Executar ou preparar — preparar:** `docs/layer2-checklist.md`. Nada público foi executado.
- **Confirmações pedidas:**
  - (a) `docs/invalidation.md` existe (versionado desde o commit `09a8550`);
  - (b) D-18 está em `docs/roadmap.md` (linha "Hash de declaração resistente a colisão"), junto com o item novo de L-18;
  - (c) o Mathlib `master` usa `leanprover/lean4:v4.36.0-rc1` (commit do Lean `c9afcddf`), lido do `lean-toolchain` do commit `e1b2403bdd31a2756e30282d62b3fa54cc95c869` em 2026-10-20.

## Q9. `native_decide` na v4.36 — DECIDIDA na instrução 13: opção (a)

**O que mudou.** Na v4.22, `native_decide` produzia um termo com `Lean.ofReduceBool`, um axioma fixo e conhecido; a política o tratava como avaliação nativa com justificativa (O-1). Na v4.36.0-rc1 (`Lean.Meta.nativeEqTrue`), o tático compila e avalia `e`, e então **adiciona ao ambiente um axioma novo, por uso**: `<dona>._native.native_decide.ax_N : e = true` (o mesmo vale para `bv_decide`). O kernel nunca reconfere esse axioma.

**O problema.** O ambiente não registra que o axioma veio do tático. Um `axiom` escrito à mão com o mesmo nome e o mesmo tipo é indistinguível (demonstrado: fixture `edges`, `uses_spoof`, travado por teste). Uma tática importada (outro arquivo do PR, ou uma dependência) também pode adicionar um axioma com essa forma sem que a Etapa A do arquivo-alvo veja nada.

**Comportamento atual (D-43), fail-closed.** O inspetor reconhece a forma (`native_auxiliary`). A política aplica as regras de justificativa e do padrão combinado como antes, e **além disso** deixa as premissas `Não resolvido` (`native_auxiliary_axiom`). Efeito na conformance: só os casos justificados mudaram, de `verified` para `unresolved` (`nd_justified`, `consumes_justified`, `add_native`); `f_bad`/`e_bad`/`e_mixed` continuam `Rejeitada`, com premissas `Não resolvido` em vez de `Conforme`. Nenhuma rejeição se perdeu.

**Opções:**
- **(a) Fail-closed permanente na Fase 0** (o atual): `native_decide` nunca sai `verified`. A justificativa O-1 continua obrigatória (sem ela, `Não conforme`), mas não basta. Simples e correto. Custo: quem usa `native_decide` com justificativa perde o `verified`. O Mathlib já proíbe `native_decide` por política própria, então o impacto no alvo principal é pequeno.
- **(b) Corroboração.** Aceitar o axioma auxiliar como avaliação nativa (e, com justificativa válida, `verified`) só se: a forma bate; a dona está no arquivo auditado; a Etapa A viu `native_decide`/`bv_decide` dentro da declaração dona; nenhum `axiom` com esse nome no arquivo; nenhum comando fail-closed no arquivo. **Não é sólido contra adversário:** `first | native_decide | tatica_importada_maliciosa` satisfaz tudo, com o axioma forjado pela tática importada.
- **(c) Reavaliação pelo auditor.** O auditor compila e avalia `e` de novo, num processo separado. Volta a executar código do PR no auditor (contra D-39) e dá a mesma confiança no compilador que o `native_decide`. Pesado.
- **(d) Reconferência pelo kernel.** O inspetor tenta reduzir `e` a `true` com o kernel (`Kernel.whnf`), com limite de esforço. Se conseguir, o axioma é admissível sem confiar no compilador: `verified` sem avaliação nativa. Se não conseguir dentro do limite, `Não resolvido`. É sólido. Mas o `native_decide` existe justamente onde o kernel é lento, então na maioria dos casos o resultado seria `Não resolvido`, como em (a), com custo de CPU.

**Recomendação: (a) na Fase 0, e (d) como item a avaliar na Fase 1.** (b) dá uma aparência de verificação que um adversário contorna. (c) contradiz D-39.

## Decisões locais da instrução 12 (para veto)

- **D-39. O inspetor não executa código do ambiente importado.** Na v4.36, `importModules (loadExts := true)` exige `enableInitializersExecution`, que executaria os `initialize` dos módulos importados — inclusive os do PR — dentro do inspetor. O inspetor passou a importar com `loadExts := false` e a ler cada extensão pelas entradas dos módulos. Consequências:
  - o `collectAxioms` oficial, sem a extensão de axiomas pré-calculados, percorre os corpos (L-20);
  - docstring Verso (sem texto bruto) conta como justificativa ausente;
  - `@[simp]`/`@[ext]` do fingerprint vêm das entradas globais gravadas, não do estado final; um `attribute [-simp]` global não é descontado (o fingerprint muda de definição; o inspetor subiu para a versão 4).

  Só o gerador da allow-list executa initializers, em manutenção, sobre código revisado.
- **D-40. Classificação dos 40 comandos novos da v4.36** (`classification_version = "4"`):
  - `allowed` (11): `#check_assertions`, `#import_path`, `#show_deprecated_modules`, `assert_not_exists`, `assert_not_imported`, `deprecated_module`, `deprecated_syntax`, `grind_annotated`, `coinductive` (declaração; entrou também nas palavras de declaração da Etapa A), `recall`, `unlock_limits` (D-41);
  - `metaprogramming`/fail-closed (29): `#guard_panic`, `#grind_lint`, `reprove` (roda tática sem resultado inspecionável, como `#check_tactic`), `with_weak_namespace` (o comando envolvido fica indentado e escaparia da checagem de coluna 0), `docs_to_verso`, a família `cbv_simproc` (6), os `declare_*config_elab*` e `def_eval_config_item` (5), os `declare_decidable_*`/`declare_eval_bin*` (5), os `register_*` (6) e `set_library_suggestions` (avalia um termo como motor de sugestões; substitui `set_premise_selector`, que era fail-closed).

  Removido: `set_premise_selector`.
- **D-41. `unlock_limits`** (zera `maxRecDepth`, `maxHeartbeats` e `synthInstance.maxHeartbeats`) é registrado pela Etapa A como os três `set_option … 0`, com `via: "unlock_limits"`, inclusive na forma `unlock_limits in`. A política existente decide: `maxHeartbeats 0` → `Rejeitada`. Testado de ponta a ponta (fixture `set-option`, `unlocked`).
- **D-42. Raízes do toolchain mudaram:** a v4.36.0-rc1 declara também `LeanChecker`, `LeanExport` e `LeanIR` (todas da distribuição do Lean). Pela regra da Q7-a (raiz declarada pelo toolchain = TCB), elas entram automaticamente. Pelo `docs/tcb.md` (ii), isso exige revisão por quem não é o autor: **pedida aqui**.
- **D-43. Axioma auxiliar nativo: fail-closed provisório.** O inspetor emite `native_auxiliary` (forma: nome `…._native.<tática>.ax_…` e tipo `@Eq.{1} Bool e Bool.true`, `e` fechado). A política tem `axioms.native_auxiliary_action`, cuja única opção é `"fail_closed"`; o schema ganhou a classificação `native_auxiliary`. Fica assim até a Q9.
- **D-44. Um toolchain suportado por vez.** A allow-list do core da v4.22.0 foi removida: sem inspetor e suíte correspondentes, ela seria promessa não verificada.
- **D-45. Fixture próprio do CI** (`tests/ci/clean-project`): os testes do `auditor-ci` usavam o cenário 06 como "projeto que passa inteiro". Com a Q9, ele deixou de passar; o fixture novo separa os testes do CI da decisão de política.
- **D-46. Convenção da dona em auxiliares `where` mudou** (L-4): o axioma auxiliar de `outer.aux` é referenciado pelo próprio `outer.aux`, que vira a dona (antes, `outer`). A justificativa passa a ser procurada onde o `native_decide` está escrito. Travado por teste.

## Rodada da instrução 13 — resoluções

- **Q9 → (a), permanente na Fase 0.** `native_decide` (e toda avaliação nativa por `nativeEqTrue`) nunca sai `verified`. Motivo registrado pelo revisor: certificar dependeria de detalhes internos do compilador que mudam entre versões, e a Fase 0 é desenhada para ser estável contra bumps de toolchain. (b), (c) e (d) foram rejeitadas, cada uma pelo motivo da pergunta. A opção (d) foi para o roadmap da Fase 1 como item de **pesquisa**, com critério de ≥ 50 % dos casos justificados e manutenção da D-39. Se não atingir o critério, fica fail-closed para sempre. Código: sem mudança (já era o comportamento da D-43). Documentação: `docs/limitations.md` (L-19), `docs/tcb.md`, `docs/roadmap.md`, `CHANGELOG.md`.
- **D-36: interpretação confirmada.** `--timeout-total-first-run` está documentado como orçamento **estendido** de um run com cache frio, não como segundo orçamento permanente, em `CHANGELOG.md` e em `docs/maintenance.md` ("Orçamentos de tempo do CI"). O SLA de 5 min é de steady-state.
- **D-42: aprovada sob condição, condição aplicada.** Ver D-47.
- **Aceitas sem modificação:** D-39, D-40, D-41, D-43, D-44, D-45, D-46.
- **Mutação em lotes:** `stage_b` → `policy` → `ci`, um grupo por vez, com commit entre os grupos. **115/115 detectadas nos 5 grupos, 0 sobreviventes.** Houve 1 sobrevivente real na Etapa B, corrigida com um teste novo. Detalhes em `docs/maintenance.md`, "Registro de execuções".
- **D-38, reprodutibilidade:** o `fanout.py` não acessa a rede nem o `master`. Grava a procedência (commit, SHA-256 do `lake-manifest.json`, `lean-toolchain`) e aceita `--expect-commit`, que sai com 2 se o checkout não for o fixado. **Correção de uma premissa:** não existe teste de drift da D-38 contra o Mathlib real na suíte, porque a suíte não baixa o Mathlib. A garantia é a procedência conferida na medição (checklist, passo 6). O mecanismo é testado em `tests/maintenance/test_layer2_tools.py`.
- **`Mathlib/Logic/Basic.lean` → `Mathlib/Basic/Logic/Basic.lean`:** registrado no `CHANGELOG.md`. Busca no repositório (`git grep`): nenhum script, fixture ou teste usa o caminho antigo. Só `docs/ci.md` e o checklist o citavam, e os dois foram atualizados.
- **Proporção de `native_decide` no Mathlib (medida agora, no commit fixado):** `tools/layer2/native_usage.py` (lexer e regra da Etapa A; comentários e strings não contam):
  - biblioteca `Mathlib`: **2 de 256 505 declarações com corpo** (0,0008 %). As duas são **código de metaprogramação**, não provas: os padrões de sintaxe `+native`/`native := true` do linter que **proíbe** avaliação nativa no Mathlib, e um campo de configuração da tática `inclusion`. **Provas da biblioteca que usam avaliação nativa: 0.**
  - `MathlibTest` (fora da biblioteca): 33 de 7 463 declarações; a maior concentração está em `MathlibTest/Algebra` (17 de 34).
  - Conclusão: o impacto da Q9 no alvo principal é nulo hoje. Os 3 relatórios da camada 2 incluem a medição, no Mathlib inteiro e por PR (checklist, passos 6 e 10).
- **Achado relacionado:** a tática `inclusion` do Mathlib (`Mathlib/Tactic/Inclusion/Core/Core.lean`) chama `nativeEqTrue` diretamente quando usada com `+native`. É exatamente o caso de "tática importada que cria o axioma auxiliar" da Q9 (b). O axioma gerado (`…._native.inclusion.ax_…`) tem a forma reconhecida pelo inspetor e sai `Não resolvido`, como o `native_decide`. Isso confirma que a opção (b) seria contornável sem adversário nenhum: basta uma tática legítima com outro nome.

## Decisões locais da instrução 13 (para veto)

- **D-47. A condição da D-42 aplicada a todas as raízes, inclusive às da v4.22.** O princípio do revisor ("as raízes que o projeto-alvo efetivamente usa") vale para todas as raízes declaradas, não só para as três novas. Medido no fecho de imports da biblioteca `Mathlib` (`e1b2403b`, 10 527 módulos, com as 8 dependências conferidas contra o `rev` do `lake-manifest.json`), as raízes usadas são `Init` (668 módulos), `Lake` (1: `Lake.Util.Casing`, via `public meta import` em `Mathlib.Tactic.Linter.TextBased`), `Lean` (741) e `Std` (215). Ficam fora `LeanChecker`, `LeanExport` e `LeanIR` (as três novas) e **também `LakeMain` e `Leanc`**, que eram TCB desde a Q7-a. A mudança é na direção fail-closed: um `@[extern]`/`@[implemented_by]` dessas raízes passa a sair `unresolved` (`module_root_not_used_by_target_project`). Se a intenção era restringir só as três novas, basta acrescentar `LakeMain` e `Leanc` à allow-list.
  - **Nota sobre "verificar contra o `lake-manifest.json`".** O manifest não lista raízes do toolchain, só pacotes. A verificação implementada é a mais próxima do que a condição pede: o fecho é calculado com cada dependência exatamente na revisão que o manifest fixa (o gerador recusa pacote fora do `rev`), e o SHA-256 do manifest fica gravado na allow-list.
- **D-48. Allow-list de raízes por toolchain, com conferência em tempo de execução.** O arquivo é `src/auditor/data/tcb_roots/<toolchain>.json`, gerado por `tools/gen_tcb_roots.py`. A fronteira passa a exigir esse arquivo. Toolchain sem arquivo, arquivo de outro toolchain, raízes declaradas diferentes das gravadas (drift do toolchain) ou raiz da allow-list não declarada → `tcb_boundary_undeclared` (exit 2).
- **D-49. Drift da D-42 em dois níveis.** (i) O cenário `06-tcb-boundary` ganhou uma declaração por raiz da allow-list (`uses_init`, `uses_lean`, `uses_std`, `uses_lake`, cada uma usando uma constante `@[extern]`/`@[implemented_by]` daquela raiz), que precisa sair TCB; se a allow-list deixar de reconhecer a raiz, o cenário falha. (ii) Um teste unitário com toolchain sintético cobre a raiz declarada e não usada (→ `unresolved`) e o drift da lista declarada. A conferência contra o Mathlib real fica no checklist da camada 2 (passo 3, `gen_tcb_roots.py --check`), porque a suíte não baixa o Mathlib.
- **D-50. `import all` no parser de cabeçalho.** `fanout.py` (e o gerador de raízes, que o reutiliza) passou a tratar `all` depois de `import` como modificador. Antes, `all` era lido como nome de módulo. Isso não mudava o ranking do fanout (o nome era descartado por ser externo), mas faria o fecho de raízes falhar com "import sem fonte".
- **D-51. Medição de avaliação nativa é léxica e declarada como estimativa.** Ela reutiliza a regra da Etapa A e conta também `bv_decide`, que a Etapa A não lista. Isso não é furo: o veredito vem da Etapa B, pela forma do axioma. O veredito por declaração continua sendo o do auditor (`native_auxiliary_axiom`), que pega também táticas como `inclusion +native`.

## Rodada da instrução 14 — resoluções (camada 1 fechada)

- **Camada 1: aceita como fechada.** 558 testes; 115/115 mutações nos 5 grupos, 0 sobreviventes e 0 puladas.
- **Q9-a: confirmada pela medição.** A medição foi registrada em `docs/tcb.md` (decisão Q7-a) e no roadmap da Fase 1, ao lado de (d) e do critério de ≥ 50 %.
- **D-47: aceita, com quatro adições obrigatórias, todas feitas:**
  1. **Renomeado:** `tcb_roots` → `target_trusted_roots`. Isso vale para o diretório `src/auditor/data/target_trusted_roots/`, para `load_target_trusted_roots` e para o campo `Boundary.trusted_roots`. No resultado da Etapa B, `boundary.toolchain_roots` passou a ser `boundary.trusted_roots`, ao lado de `boundary.declared_roots`. O JSON ganhou o campo `meaning`, que diz o que ele significa e o que não significa. O nome do gerador (`tools/gen_tcb_roots.py`) ficou como estava, porque é o citado no texto da instrução.
  2. **L-21** em `docs/limitations.md` (a Fase 0 é voltada ao Mathlib; outros alvos geram o próprio arquivo; podem aparecer falsos positivos).
  3. **Roadmap da Fase 1:** descoberta automática de raízes para alvos arbitrários, com a mesma política de verificação contra o `lake-manifest.json`.
  4. **`docs/tcb.md`:** tabela com as raízes declaradas pelo Lean v4.36, as usadas pelo Mathlib `e1b2403b` e as que estão em `target_trusted_roots`.
- **D-48, D-49, D-50: aceitas.** **D-51: aceita com nota.** A contagem exata, por compilação, ficou registrada como item da Fase 1 no roadmap.
- **D-38: aceita.** Registrada como **L-22** em `docs/limitations.md`.
- **`rea` (MCP) e a suíte:** nenhum teste depende de servidor MCP. `git grep` em `tests/`, `src/`, `tools/` e `pyproject.toml` não acha referência, e a suíte inteira da camada 1 (558) rodou **depois** de o WSL ser desligado, com o `rea` desconectado.
- **Preparação da camada 2:**
  1. **Critérios de aborto para falha que não é de infraestrutura.** Os que já existiam cobriam os sinais de ambiente (passo 5) e `unknown_command`, `inspector_disagreement` e `missing_constants` (passo 7). **Não** cobriam:
     - o lema de sonda não sair `verified`;
     - uma declaração que o PR não tocou sair `Rejeitada`, `Não conforme` ou `Não resolvido`;
     - `native_auxiliary_axiom` na biblioteca;
     - `tcb_boundary_*`;
     - `--check` divergente no meio da medição.

     O checklist ganhou a seção "Falha que não é de infraestrutura", que vale em todos os passos: parar, não ajustar nada para passar, não repetir, trazer os artefatos. A classificação fica fora do run.
  2. **Teste de fumaça (passo 3b, antes de qualquer PR).** Roda `auditor-ci run` num único arquivo (`Mathlib/Logic/Hydra.lean`) no commit fixado, com `--build-cache miss`, e confere `cache_state: cold`, `first_run: true`, `infra_failed: false`, `exit_code` 0, nenhum `allowlist_unavailable` nem outro sinal de ambiente, e todas as declarações `verified`. Os comandos foram executados aqui sobre o fixture `tests/ci/clean-project`, com a mesma CLI e as mesmas checagens: `cold`, `first_run: True`, `exit_code` 0, nenhum sinal de ambiente.
- **Flutuação observada (sem causa conhecida).** Depois do renome, `test_06_toolchain_extern_does_not_trigger` falhou uma vez, numa execução combinada com outros arquivos cuja saída não foi guardada. Em seguida passou 4 vezes: 3 sozinho e 1 na mesma combinação. A causa não é conhecida, e nenhuma é afirmada aqui. A partir de agora, as execuções por partes guardam o log de qualquer falha. Se voltar a acontecer, haverá evidência.

## Rodada da instrução 15 — camada 2, primeiro `auditor-prep`

O primeiro `auditor-prep` no fork (`Enzo47961/mathlib4`, `auditor-base` = `847592d` sobre `e1b2403b`; run 39656457392) parou no passo 3. O comportamento fail-closed na fumaça foi o esperado: sem allow-list, 0 `verified` e 20 `unresolved` (`stage_a_unrecognized`). As três falhas abaixo são bugs reais das ferramentas, encontrados pelo ambiente-alvo e indetectáveis na camada 1 (L-23).

- **D-52: aprovada.** O gerador extrai só das `lean_lib` `@[default_target]` (ou `--lib`).
  - **Causa:** `project_modules()` importava todo `.olean` do build, inclusive a biblioteca `Cache` do Mathlib, que define `Lean.Name.fromComponents` como `Mathlib.Lean.Name`. A D-6 supunha um projeto com uma biblioteca só.
  - **Testes:**
    - (a) `test_extraction_ignores_non_target_library`: o mini-projeto ganha uma segunda `lean_lib` (`Tool`) que define o mesmo nome que a `Mini`. A extração padrão usa só a `Mini`, e pedir as duas (`--lib Mini --lib Tool`) falha com exit 2, o que prova que a colisão do fixture é real.
    - Leitura do lakefile `.lean` e `.toml`; lakefile sem `@[default_target]` → erro que pede `--lib`.
    - (b) Mutações no grupo `allowlist`: voltar a listar tudo; aceitar `defaultTargets` que não são `lean_lib`; aceitar lakefile sem alvo.
    - (c) O caso real (Mathlib + `Cache`) é conferido pelo próximo `auditor-prep`.
- **D-53: aprovada, opção forte (normalizar, não só documentar).** CRLF → LF antes do hash em `env_pin` e em `gen_tcb_roots.py`, e também na procedência do `fanout.py`, para os três hashes do mesmo manifesto baterem. SHA-256 do conteúdo normalizado (não o blob do git, que é SHA-1; D-18).
  - **Versões:** `ENV_PIN_VERSION` `2`; `generator_version` `3`.
  - **Regeneração:** `target_trusted_roots` foi regenerado no clone local (Windows, CRLF) do `e1b2403b`. Só o hash mudou, para `f77f47db…`, o mesmo que o runner Linux calculou: evidência direta de que a normalização funciona entre os sistemas.
  - **Testes:**
    - `test_env_pin_ignores_crlf`;
    - `test_allowlist_survives_line_ending_change` (gerada em LF, usada em CRLF, e o inverso; Etapa A e `--check`);
    - `test_gen_tcb_roots_manifest_hash_ignores_crlf` (gerador e `fanout`);
    - o arquivo versionado travado em `f77f47db…`.
  - **Mutações:** uma em cada lugar.
  - **Nota sobre a D-10:** o `.gitattributes` (`* -text`) protege só o repositório do auditor, não o projeto-alvo, que é clonado com a configuração de quem clona. A normalização é a garantia; a D-10 continua valendo para os arquivos do próprio auditor.
- **D-54: aprovada como proposta, com o invariante explícito.** `--check` aceita `HEAD` ≠ commit gravado só se o gravado for ancestral, a árvore de trabalho (não só o `HEAD`) diferir apenas em `.github/` e nenhum `.lean` mudar, nem dentro de `.github/`. Registrado como **L-24**: relaxamento específico da medição em fork; no repositório real vale o check estrito.
  - **Testes:**
    - aceito: só `.github/`;
    - rejeitados (5): `README.md`, um `.lean` com o mesmo fecho, `.github/Gen.lean`, mudança não commitada, commit irmão (não ancestral, mas que só difere em `.github/`);
    - check estrito quando `HEAD` = commit gravado.
  - **Mutações:** novo grupo `gen_tcb_roots` (8).
  - **Execução real:** no clone local do fork (`847592d`), o `--check` passou pelo caminho de fork.
- **D-55: aprovada.** `runs-on: ubuntu-24.04` no workflow reutilizável, no `ci.yml`, nos templates e no `auditor-prep` do fork. A atualização das actions de Node 20 fica para uma rodada separada, fora da camada 2, com registro no CHANGELOG.
- **`syntax_extension_declared` com `command: "?"`:** será verificado na próxima fumaça. Se persistir com a allow-list do Mathlib presente, é falha que não é de infraestrutura e será tratado como bug; se desaparecer, fica registrado como consequência da falta de allow-list.
- **Registro pedido como "L-19":** o número L-19 já existe (axioma auxiliar de avaliação nativa, Q9). O texto foi registrado como **L-23**, e o relaxamento da D-54 como **L-24**.
- **Revalidação:** só os grupos de mutação tocados (`allowlist` e o novo `gen_tcb_roots`) foram re-rodados. `policy`, `ci`, `stage_a` e `stage_b` continuam validados pelos commits anteriores, porque o código deles não mudou. A suíte completa foi re-rodada.

## Correções feitas na retomada (sessão no Windows)

- O código da Etapa B e da Q5 da sessão anterior não foi preservado: só o `stage_a.py` (já com suporte a allow-list de projeto) e os documentos. A Q5 e a Etapa B foram reimplementadas a partir das decisões registradas.
- Portabilidade: a saída do Lean passou a ser decodificada como UTF-8 explicitamente (no Windows, o padrão é cp1252, o que quebrava dois testes de ground truth com nomes Unicode).
