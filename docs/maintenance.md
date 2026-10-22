# Manutenção

Allow-list da Etapa A, inspetor, testes de mutação e fixação de versões dos workflows.

## O que é mantido e por quem

A allow-list tem duas partes de origem diferente:

| Parte | Origem | Arquivo |
|---|---|---|
| Lista de comandos | **extraída mecanicamente** do toolchain (categoria `command` do parser, via `src/auditor/lean/Dump.lean`) | gerada em `src/auditor/data/allowlist/<toolchain>.json` |
| Classificação de risco (`syntax_extension`, `metaprogramming`) e tokens de continuação | **mantida à mão**, com critério escrito | `tools/gen_allowlist/classification.toml` |

Comando extraído que não está classificado cai em `allowed`. Por isso, **ao subir o toolchain, todo comando novo precisa de revisão humana**: o gerador lista o que mudou, mas não julga o risco.

## Teste de defasagem

`tests/maintenance/test_allowlist_fresh.py` roda `gen.py --check`: roda o extrator com o `lean-toolchain` fixado e falha se o arquivo versionado não corresponder exatamente. O gerador também falha se `classification.toml` citar um comando que não existe no toolchain, para que a classificação não apodreça quando o Lean remover sintaxe.

Em tempo de execução, a Etapa A seleciona a allow-list pelo `lean-toolchain` **do projeto-alvo**. Sem arquivo para aquele toolchain, o resultado é `allowlist_unavailable` (fail-closed). Allow-list cujo conteúdo declara outro toolchain é rejeitada.

## Procedimento ao subir o toolchain

É o procedimento de cada bump do Mathlib. Foi executado de ponta a ponta na subida
`v4.22.0 → v4.36.0-rc1` (instrução 12); as notas "Na subida para a v4.36" registram o que cada
passo encontrou.

1. **Fixar a versão alvo.** Ler o `lean-toolchain` do Mathlib no commit escolhido e anotar o
   commit. Instalar: `elan toolchain install <toolchain>`.
2. **Atualizar `lean-toolchain`** na raiz e em todos os fixtures (`git ls-files | grep lean-toolchain$`;
   `test_fixture_toolchain_matches_root` aponta cópias divergentes).
3. **Extrator da allow-list.** Rodar `python tools/gen_allowlist/gen.py`. Se `Dump.lean` não
   compilar, ajustar à API nova. *Na v4.36: `String.trim` → `trimAscii`; `importModules
   (loadExts := true)` passou a exigir `enableInitializersExecution` (aceito só no gerador; ver
   `docs/tcb.md`, D-39).*
4. **Classificar os comandos novos.** O gerador lista o que mudou e recusa classificação que cite
   comando inexistente. Comando novo não classificado cai em `allowed`, então **cada um** passa pelo
   critério de `classification.toml` (L-17), lendo a definição no fonte do toolchain. Na dúvida,
   fail-closed. Comando com efeito equivalente a uma opção da política (ex.: `unlock_limits`) é
   registrado pela Etapa A como essa opção. Subir `classification_version`. *Na v4.36: 40 comandos
   novos e 1 removido (`set_premise_selector`); classificação `4` (D-40, D-41).*
5. **Remover a allow-list do toolchain anterior.** O auditor só suporta o toolchain testado; uma
   allow-list sem inspetor e suíte correspondentes seria promessa não verificada.
6. **Inspetor.** Compilar (`stage_b.ensure_inspector`) e ajustar à API nova. Comparar
   `src/lean/Lean/Util/CollectAxioms.lean` do toolchain novo com `directDeps` em `Inspect.lean`
   (o fecho independente precisa espelhar o percurso oficial). Conferir que o inspetor continua
   sem executar código importado (`loadExts := false`). Subir `inspectorVersion` e
   `INSPECTOR_VERSION` juntos. *Na v4.36: `CollectAxioms.collect` virou privado e passou a usar
   axiomas pré-calculados nos `.olean`; o tipo de um axioma passou a ser percorrido; docstrings
   lidas com `findInternalDocString?` (texto bruto); `@[simp]`/`@[ext]` lidos das entradas dos
   módulos.*
7. **Rodar a suíte inteira** e tratar cada falha como sinal de que a Etapa A ou B dependia de um
   detalhe da versão. Separar o que é mudança mecânica (nomes, API) do que muda o significado de um
   resultado: o segundo tipo é decisão de política, vai para o revisor, e enquanto isso o
   comportamento é fail-closed. *Na v4.36: `native_decide` passou a adicionar um axioma por uso
   (L-19, Q9); a convenção da dona de `where` mudou (L-4).*
8. **Fronteira de TCB.** As raízes de TCB são o `target_trusted_roots` de cada toolchain
   (`src/auditor/data/target_trusted_roots/<toolchain>.json`): as raízes que o projeto-alvo de fato usa,
   **não** todas as que o toolchain declara (D-42). Regenerar com o Mathlib no commit fixado
   e as dependências nas revisões exatas do seu `lake-manifest.json`:
   `python tools/gen_tcb_roots.py --sysroot <sysroot> --project <mathlib> --root Mathlib`.
   O gerador confere cada pacote contra o manifest (commit = `rev`) e recusa se não bater. O
   canário `test_06_tcb_boundary_canary` confere a lista declarada pelo toolchain, e o cenário
   `06-tcb-boundary` tem uma declaração por raiz da allow-list (`uses_<raiz>`) que precisa sair
   TCB. Raiz nova ou removida vai para revisão por quem não é o autor (`docs/tcb.md`, (ii)).
   *Na v4.36: o toolchain passou a declarar `LeanChecker`, `LeanExport` e `LeanIR`; o fecho do
   Mathlib usa só `Init`, `Lake`, `Lean` e `Std` (D-42, D-47).*
9. **Ground truth.** `tests/conformance/test_ground_truth.py` roda `#print axioms` do próprio Lean
   nos fixtures. Atualizar só o que o Lean passou a imprimir de outro jeito, nunca o veredito dos
   enunciados falsos (as negações continuam compilando).
10. **Mutação.** Rodar `python tools/mutation/run.py <grupo>` **um grupo por vez**, nesta ordem:
    `stage_a`, `allowlist`, `stage_b`, `policy`, `ci`. Conferir 0 sobreviventes e fazer commit
    entre os grupos. Se o processo for interrompido no meio, `git status` mostra o arquivo que
    ficou mutado: restaurar com `git checkout -- <arquivo>` antes de qualquer outra coisa. O
    grupo `policy` é o mais pesado, porque roda a conformance a cada mutação.
11. **Registrar.** `CHANGELOG.md` (incompatível: toolchain fixado), README ("Ambientes"),
    `docs/tcb.md` (raízes), e as decisões novas em `docs/proposed-improvements.md`.
12. **Revisão.** Classificação de comandos, fronteira de TCB e qualquer mudança de veredito exigem
    revisão por alguém que não é o autor.

## Orçamentos de tempo do CI (D-21, D-28, D-36)

Três limites, com nomes que dizem o que medem (D-36):

| Limite | CLI | Entrada do workflow | Padrão | O que é |
|---|---|---|---|---|
| Total do PR | `auditor-ci run --timeout-total` | `timeout-total-seconds` | 300 s | **O** orçamento: o SLA de 5 min, em steady-state (`cache_state` `warm`/`delta`). Relógio desde o trigger, preparação incluída. |
| Total do PR com cache frio | `auditor-ci run --timeout-total-first-run` | `timeout-total-first-run-seconds` | 900 s | **Orçamento estendido de um run com cache frio**, não segundo orçamento permanente. Só vale com evidência positiva de `cache_state: cold`, o que acontece no primeiro run do fork ou depois de o cache ser despejado. Sinal ausente conta como cache quente. |
| Por arquivo | `auditor check --timeout-file` / `auditor-ci run --timeout-file` | `timeout-file-seconds` | 90 s | Limite de um arquivo; estourar encerra a auditoria do PR (exit 2). |

O run com cache frio declara `first_run: true`. Se passar dos 300 s sem estourar os 900 s, não
falha: ganha `cache_cold_extension: true` e o label `auditor-first-run`. Medições da camada 2
nunca usam um run `cold` como steady-state (`docs/layer2-checklist.md`, passo 7). Mudar um
padrão é mudança de SLA: vai para o revisor e para o `CHANGELOG.md`.

## Tabela de confusables (TR39)

`src/auditor/data/unicode/confusables-16.0.0.txt` é cópia versionada do Unicode TR39 16.0.0 (termos de uso no cabeçalho do arquivo). Atualizar a versão é mudança explícita: novo arquivo com a nova versão no nome, e o caminho atualizado em `stage_a.py`.

## Allow-list de projeto (Mathlib e outros)

Comandos definidos por um projeto ou por suas dependências (o Mathlib define `lemma`, `alias`, `assert_not_exists`, …) não estão na allow-list do core. Para auditar arquivos desse projeto:

1. No projeto já compilado (no Mathlib: `lake exe cache get`), rodar `auditor-gen-allowlist --project <dir>`. O gerador roda `lake build` nas bibliotecas-alvo (as `lean_lib` `@[default_target]` do lakefile, ou as de `--lib`; D-52), importa todos os módulos delas, extrai os comandos e grava `<dir>/.auditor/allowlist.json` com o `env_pin` (`lean-toolchain` + `lake-manifest.json`).
2. Ler a lista `unclassified` do arquivo gerado: são os comandos novos do projeto. Enquanto estiverem ali, são fail-closed.
3. Classificar cada um em `<dir>/.auditor/classification.toml` (chaves `classification_version`, `allowed`, `syntax_extension`, `metaprogramming`), com o mesmo critério de `tools/gen_allowlist/classification.toml`. A classificação não pode citar comandos do core nem comandos inexistentes; o gerador recusa.
4. Regenerar. `--check` falha se o arquivo não corresponder ao ambiente atual.
5. Classificação é política: exige revisão por alguém que não é o autor.

O `env_pin` usa o `lake-manifest.json` com fim de linha normalizado (D-53): um clone CRLF e um LF do mesmo commit dão o mesmo pino. Ao mudar o `lake-manifest.json` ou o `lean-toolchain`, a allow-list fica obsoleta e a Etapa A falha fechada (`allowlist_stale`) até ser regenerada.

**A allow-list do Mathlib é evidência da camada 2**, gerada no fork do mantenedor. Ela não bloqueia a camada 1, cujo requisito é o gerador testado contra um projeto Lake arbitrário (`tests/allowlist`). A Fase 0 não verifica a correção semântica da classificação, só a correspondência com o pino (L-16).

## Inspetor da Etapa B

O inspetor (`src/auditor/lean/Inspect.lean`) é compilado com o toolchain do projeto-alvo e guardado em cache (`%LOCALAPPDATA%\auditor\inspector` no Windows, `$XDG_CACHE_HOME/auditor` ou `~/.cache/auditor` nos demais; `AUDITOR_CACHE` sobrescreve). A chave do cache é o hash do fonte + toolchain, então qualquer mudança no inspetor gera um binário novo.

Ao mudar `Inspect.lean`, subir `inspectorVersion` e `INSPECTOR_VERSION` (`stage_b.py`) juntos; um teste trava a divergência.

O percurso de dependências espelha `Lean.CollectAxioms.collect` do toolchain fixado. Ao subir o toolchain:
1. comparar `src/lean/Lean/Util/CollectAxioms.lean` do novo toolchain com `directDeps` em `Inspect.lean`;
2. rodar `tests/stage_b`. Os testes comparam o inspetor com `#print axioms` e travam as convenções de que a atribuição depende.

## Convenção de nomes auxiliares de `native_decide`

A atribuição de `native_decide` à declaração dona depende da convenção `X._proof_N` do compilador (L-4). Ela está travada por testes de regressão em `tests/stage_b` (`test_05_owner_attribution`, `test_edges_where_auxiliary_owned_by_top_level_declaration`, `test_edges_private_declaration_reported_and_owned`). A subida do toolchain precisa passar por eles.

## Testes de mutação

Um teste verde só é evidência se ficar vermelho quando o código está errado. Esta disciplina já encontrou falhas reais duas vezes: um falso resultado de mutação causado pelo `pythonpath` do pytest (Etapa A) e 4 buracos de teste na Policy, todos corrigidos. Ela não depende de memória: o catálogo e o executor estão versionados.

- **Catálogo:** `tools/mutation/catalog.py`. Grupos `stage_a`, `allowlist`, `stage_b`, `policy`, `ci` e `gen_tcb_roots` (este desde a instrução 15); cada mutação é (arquivo, trecho original, trecho mutado), e cada grupo declara os testes que precisam acusá-la.
- **Executor:** `python tools/mutation/run.py [grupo ...]`. Aplica cada mutação, roda os testes do grupo com `-x` e restaura o arquivo a partir de uma cópia em memória, também em caso de erro. Termina com exit 1 se alguma mutação **sobreviveu** (buraco nos testes) ou foi **pulada** (padrão não encontrado).
- **Integridade do catálogo:** `tests/maintenance/test_mutation_catalog.py`, rápido e parte da suíte normal, falha se algum padrão deixar de ocorrer exatamente uma vez no código. Assim, refatorar uma checagem obriga a atualizar a mutação correspondente, em vez de ela virar uma mutação "pulada" sem ninguém notar.

**Quando rodar:**
1. ao fechar cada etapa;
2. ao mudar qualquer regra de política (a mudança de regra exige auditoria por outra pessoa, e o resultado da mutação é parte da evidência dessa auditoria);
3. ao subir o toolchain.

**Ao adicionar uma checagem nova,** acrescente ao menos uma mutação que a desligue e confirme que ela é detectada. Uma mutação sobrevivente se resolve escrevendo o teste que falta, nunca removendo a mutação.

**Armadilhas já encontradas:**
- O pytest com `pythonpath = ["src"]` importa o código do repositório. Mutar uma cópia em outro diretório faz toda mutação "sobreviver" falsamente; o executor muta no lugar.
- Strings com barra invertida em scripts gerados via heredoc do shell perdem o escape; o catálogo usa strings *raw* num arquivo Python.
- **Processo morto de fora não restaura o arquivo.** A restauração em caso de erro cobre exceções, não um processo encerrado pelo sistema (falta de memória, instrução 12). Depois de uma interrupção, `git status` mostra o arquivo mutado; conferir o diff (deve ser exatamente uma mutação do catálogo) e restaurar com `git checkout -- <arquivo>`. Por isso a mutação roda um grupo por vez, com commit entre os grupos.

**Registro de execuções** (uma linha por grupo; commit entre grupos):

| Data | Commit do código | Grupo | Detectadas | Sobreviventes / puladas |
|---|---|---|---|---|
| 2026-10-20 | `0b9d2bc` (v4.36.0-rc1) | `stage_a` | 9/9 | 0 |
| 2026-10-20 | `0b9d2bc` | `allowlist` | 9/9 | 0 |
| 2026-10-21 | `0b9d2bc` | `stage_b` | 16/17 | **1 sobrevivente**: `.axiomInfo v => v.type.getUsedConstants` → `#[]` (o fecho não percorria o tipo de axioma em nenhum fixture). Teste novo: `edges`, `via_axiom_type` (chega a `sorryAx` só pelo tipo de `ax_over_sorry`). A mutação re-rodada sozinha foi detectada (`inspector_disagreement`). Resultado: 17/17. |
| 2026-10-21 | `064f170` | `policy` | 45/45 (36 anteriores + 9 da allow-list de raízes, D-42) | 0 |
| 2026-10-21 | `6532f5e` | `ci` | 22/22 | 0 |
| 2026-10-21 | `6532f5e` | `stage_b` (re-rodado sobre o código final) | 17/17 | 0 |

| 2026-10-21 | `b73bc6d` (renome `target_trusted_roots`) | `policy` | 45/45 | 0 |
| 2026-10-21 | `b73bc6d` | `stage_b` | 17/17 | 0 |

Depois do renome (`b73bc6d`), a suíte inteira deu 558 passed. O `ci` não mudou desde o `6532f5e`.

Os grupos `stage_a` e `allowlist` foram rodados no `0b9d2bc`. O código e os testes deles não mudaram até o `6532f5e` (`git diff --stat` vazio), então o resultado vale para o código final. **Estado em 2026-10-21: 5 grupos, 115/115 detectadas, 0 sobreviventes, 0 puladas.** A suíte inteira, rodada por partes, deu 558 passed e 0 falhas.

**Instrução 15 (camada 2: D-52, D-53, D-54).** A partir daqui, a mutação e a suíte rodam no GitHub Actions (Linux, `ubuntu-24.04`), não na máquina do mantenedor. A mutação usa o workflow `auditor-mutation` do fork de medição; a suíte usa o `ci.yml` deste repositório, em todo push.

| Data | Commit do código | Grupo | Detectadas | Sobreviventes / puladas |
|---|---|---|---|---|
| 2026-10-21 | `2a4306b` | `allowlist` (9 anteriores + 4: D-52 e D-53) | 13/13 | 0 |
| 2026-10-21 | `2a4306b` | `gen_tcb_roots` (grupo novo: D-53 e D-54) | 8/8 | 0 |

Execução da mutação: `Enzo47961/mathlib4`, run 39665194703 (5 min 21 s). Os grupos `stage_a`, `stage_b`, `policy` e `ci` não foram re-rodados: o código deles não mudou desde os commits registrados acima.

**Suíte no Linux** (`ci.yml`, run 39664969425 sobre `2a4306b`): 585 passed, **3 failed**. As 3 falhas já aconteciam no `bcdccc6` (run 39655475487: 555 passed, 3 failed), o primeiro run da suíte fora do Windows, e não vêm das mudanças da instrução 15. São testes que dependem da máquina (L-23):
- `tests/stage_b/test_stage_b.py::test_timeout_is_not_success` e `tests/cli/test_cli.py::test_artificial_timeout_never_success` pedem um timeout de 0,01 s, mas a Etapa B aplica um piso de 1 s (`max(1.0, …)` em `stage_b.analyze`). No runner, o fixture compila em menos de 1 s, e o timeout não dispara (`success`). Não é fail-open: o build terminou dentro do limite efetivo.
- `tests/ci/test_ci.py::test_all_pass` espera `cache_state: warm`, mas, num runner sem cache do inspetor, o primeiro run sai `cold`.

A correção desses testes depende de decisão do revisor (instrução 15: nada de novo no auditor até o próximo `auditor-prep`).

**Instrução 16 (D-56, D-57, D-58).** Os 3 testes foram corrigidos (D-58): os dois de timeout usam um fixture gerado (`conftest.slow_lean_source`, 800 teoremas por `decide`, ~13 s no Windows), que compila em segundos em qualquer máquina, e conferem que a duração medida passou de 1 s; o `test_all_pass` aquece o cache do inspetor antes (`ci._prebuild_inspector`) e declara que testa o caminho warm. **A suíte do `ci.yml` (Linux) é a referência da camada 1**; a execução local é conveniência.

| Data | Commit do código | Grupo | Detectadas | Sobreviventes / puladas |
|---|---|---|---|---|
| 2026-10-21 | `e6e9f62` | `stage_a` (9 + 4: D-56, D-57) | 13/13 | 0 |
| 2026-10-21 | `e6e9f62` | `allowlist` (re-rodado: `stage_a.py` mudou) | 13/13 | 0 |
| 2026-10-21 | `e6e9f62` | `stage_b` (testes mudaram: D-58) | 17/17 | 0 |
| 2026-10-21 | `e6e9f62` | `policy` (inclui `tests/cli`, que mudou: D-58) | 45/45 | 0 |
| 2026-10-21 | `e6e9f62` | `ci` (testes mudaram: D-58) | 22/22 | 0 |

Execução: `auditor-mutation`, run 39671405280 (20 min, Linux): 110/110. Suíte no `ci.yml` (run 39670595679 sobre `e6e9f62`): **609 passed, 0 failed**. O grupo `gen_tcb_roots` (8/8 no `2a4306b`) não foi re-rodado: o código e os testes dele não mudaram. **Estado em 2026-10-21: 6 grupos, 118/118 detectadas, 0 sobreviventes, 0 puladas.**

| Data | Commit | Grupo | Detectadas | Sobreviventes |
|---|---|---|---|---|
| 2026-10-21 | `382b5a5` | `stage_a` | 13/13 | 0 |
| 2026-10-21 | `382b5a5` | `allowlist` (+10: D-52/D-53, L-26) | 18/19 | **1** |
| 2026-10-21 | `382b5a5` | `stage_b` | 17/17 | 0 |
| 2026-10-21 | `382b5a5` | `policy` | 45/45 | 0 |
| 2026-10-21 | `382b5a5` | `ci` (testes de timeout com fixture lento) | 22/22 | 0 |
| 2026-10-21 | `382b5a5` | `gen_tcb_roots` (+1: D-59) | 9/9 | 0 |

Execução: `auditor-mutation`, run 39694466059 (31 min, Linux): 124 detectadas, **1 sobrevivente**, 0 puladas. Suíte no `ci.yml` (run 39694408989 sobre `382b5a5`): **627 passed, 0 failed**. Sobrevivente: `classification_review_status` trocado pela constante `"author-self-review"` (`src/auditor/tier1/stage_a.py`). Os testes só cobriam a classificação auto-revisada, e uma constante igual ao único valor testado passava. Lacuna de teste, não de código. Corrigido com `test_classification_review_status_values` (os 6 caminhos: `core-only`, `no-project-classification`, `undeclared` sem declaração e com `reviewed_by` nulo, `human-reviewed`, `independent-ai-reviewed`). Conferido localmente: com a mutação aplicada, 4 dos 6 casos falham. Re-rodado sobre `fe95112` (run 39698136489): `allowlist` **19/19**, 0 sobreviventes. Suíte no `ci.yml` (run 39698083967 sobre `fe95112`): **633 passed, 0 failed**. **Estado em 2026-10-22: 6 grupos, 125/125 detectadas, 0 sobreviventes, 0 puladas.** O fork segue com o auditor `382b5a5`: de `382b5a5` para `fe95112` só mudaram um teste e este documento.

**Instrução 20 (D-61, A2, D-62).** Grupos afetados re-rodados sobre `7f7238d`:

| Data | Commit | Grupo | Detectadas | Sobreviventes |
|---|---|---|---|---|
| 2026-10-22 | `7f7238d` | `ci` (+10: D-61, A2, D-62) | 32/32 | 0 |
| 2026-10-22 | `7f7238d` | `allowlist` | 19/19 | 0 |
| 2026-10-22 | `7f7238d` | `stage_b` | 17/17 | 0 |

Execução: `auditor-mutation`, run 39758578127 (Linux): 68 detectadas, 0 sobreviventes, 0 puladas. Suíte no `ci.yml` (run 39758445713 sobre `7f7238d`): **662 passed, 0 failed**. Os grupos `stage_a`, `policy` e `gen_tcb_roots` não foram re-rodados: de `fe95112` para `7f7238d` o código e os testes deles não mudaram (`git diff --stat` só toca `ci.py`, um comentário de `allowlist.py`, workflows, testes de CI e docs). **Estado em 2026-10-22: 6 grupos, 135/135 detectadas, 0 sobreviventes, 0 puladas.**



## Teste de referência dos workflows de cache (A2, instrução 21)

Um cache que sempre dá hit não testa o caminho que salva. Com o branch base aquecido (D-61), todo PR restaura o inspetor do base e o passo de salvar do A2 nunca roda. **Todo workflow que salva cache é testado assim, ao ser criado ou alterado:**

1. Apagar o cache em questão no ref do base (`gh api -X DELETE repos/<fork>/actions/caches/<id>`; listar com `gh api repos/<fork>/actions/caches`). Só caches regeneráveis pelo `auditor-warm-cache`.
2. Re-rodar um PR cujo job sai **vermelho** (`gh run rerun <run>`). Esperado: miss, build, job vermelho, e mesmo assim o passo de salvar `success`; o cache aparece com ref `refs/pull/N/merge`.
3. Re-rodar de novo. Esperado: `inspector: hit` no `outcome.json`.
4. Re-aquecer o base (`gh workflow run auditor-warm-cache --ref auditor-base`) e conferir que os caches voltaram a `refs/heads/auditor-base`.

Execução de referência (2026-10-22, auditor `7f7238d`): cache do inspetor do base apagado (id 9332096105); PR #6 (`Connect.lean`, exit 1) re-rodado (run 39760129710): tentativa 2 construiu e salvou em `refs/pull/6/merge`; tentativa 3 `inspector: hit`, `warm`, 125,2 s; base re-aquecido (run 39761275384).

## Testes de referência dos modos de falha do CI (passos 8 e 9, instrução 22)

**Passo 8: timeout de infraestrutura.** Num branch do fork, acrescentar `timeout-file-seconds: 5` ao `with:` do `auditor-tier1.yml` e tocar um `.lean` cuja auditoria leve mais que isso (`Mathlib/Logic/Hydra.lean`, ~13 s). Abrir o PR e nunca fazer merge. Esperado e verificado (PR #9, run 39818035267, auditor `7f7238d`):
- arquivo `timeout`, `timeout_kind: file`, `duration_s` 5,54 com `timeout_s` 5;
- `exit_code: 2`, `infra_failed: true`, `audit_failed: false`, `timeout_aborted: true`;
- `cache_state: warm`, ou seja, o timeout não se confunde com cache frio;
- job **verde**, PR `mergeable` (não bloqueia);
- label `auditor-failed-infra` (não `auditor-first-run`);
- nenhum comentário no PR.

**Passo 9: `@auditor report`.** O dono do fork comenta `@auditor report` num PR já auditado. Esperado: um único comentário de `github-actions` com o sumário, começando por "Pedido por um humano". Primeira execução (PR #8, run 39818084000, 2026-10-22): **falhou**. Respondeu "nenhuma execução para o commit `769e23c`", embora a execução 39813522377 existisse e estivesse concluída. Causa: o filtro `head_sha` da API de execuções (usado por `gh run list --commit`) não é determinístico. A mesma consulta, repetida, alternou entre 0 e 1 resultado nos três endpoints (`/actions/runs`, `/actions/workflows/<arquivo>/runs`, `/actions/workflows/<id>/runs`). Não depende da versão do `gh`: 2.101.0 e 2.103.0 deram os dois resultados. Correção no modelo `auditor-report.yml`: listar sem filtro no servidor e selecionar o commit no cliente; execução ainda em andamento tem mensagem própria, em vez de "falha de infraestrutura". Conferida contra o fork (PRs #1, #5, #8, #9, três vezes cada). Teste e 3 mutações no grupo `ci`.

Não testado na camada 2: um comentário de quem **não** tem acesso ao repositório não dispara o job. Exigiria uma segunda conta. A garantia é a condição `author_association` do job, travada por `test_report_workflow_requires_explicit_human_request`.

## Fixação de versões nos workflows (D-25)

**Todas as actions em workflows do auditor são pinadas por SHA; atualização é PR que muda o SHA e é revisado.** Vale para este repositório (`.github/workflows/`) e para os modelos do repositório-alvo (`ci/templates/`). Tag é mutável; SHA de commit não. Se o publicador de uma action for comprometido, uma tag flutuante é um vetor de ataque à cadeia de suprimentos, exatamente o tipo de troca silenciosa que o auditor existe para detectar.

- Formato: `uses: actions/<nome>@<SHA de 40 hex> # vX.Y.Z`. O comentário com a versão é obrigatório e serve à revisão; `tests/ci/test_workflows.py` exige os dois.
- Para atualizar: obter o SHA do commit da tag nova (`git ls-remote --tags https://github.com/actions/<nome>`; em tag anotada, usar a linha `^{}`), trocar SHA e comentário juntos, ler o changelog da action e abrir PR. Quem revisa confere o SHA contra a tag.
- **elan:** o `elan-init.sh` baixa a release `latest` do elan, então fixar a tag do script não fixa o elan (D-35). Os workflows baixam o binário da release fixada (`ELAN_VERSION`) e conferem `ELAN_SHA256` antes de executar. Para atualizar: baixar `elan-x86_64-unknown-linux-gnu.tar.gz` da release nova, calcular o SHA-256, trocar os dois valores em `ci.yml` e `auditor-tier1.yml` no mesmo PR.
- Resíduos não fixados por hash no CI (L-18): o toolchain Lean que o elan baixa a partir de `lean-toolchain` e as dependências Python resolvidas pelo pip. As versões efetivas entram na TCB do relatório (`kernel.githash`, `aggregator.python_dependencies`).
