# Changelog

Mudanças que afetam quem usa o auditor (CLI, `auditor-ci`, workflows, relatório). A Fase 0
ainda não está em produção (a camada 2 não começou), então mudanças incompatíveis são feitas
sem período de transição.

## Não lançado

### Fase 0 — closed at layer 1 + layer 2 measurement level, author-self-review declared, pending steps 8-9 (2026-10-22)
- Fechamento declarado pelo revisor (instrução 22). Evidência consolidada em `docs/phase0-report.md`:
  3 PRs `warm` no caminho de sucesso abaixo de 5 min (126 s, 130 s, 138 s), sonda do fanout
  `verified` (`Data/String/Defs.lean`, 9/9), caminho fail-closed reportado à parte (PR #7), 662
  testes, mutação 135/135, allow-list idêntica byte a byte, todos os relatórios com
  `classification_review_status: author-self-review` e `project_dirty: false`.
- **Condições antes de a Fase 1 abrir:** passos 8 (timeout / `auditor-failed-infra`) e 9
  (`@auditor report` a pedido humano) do checklist da camada 2; pendência da revisão externa
  descartada fechada (respondida ou declarada como não respondida).
- Prioridades P0 da Fase 1 em `roadmap.md`: `@[implemented_by]` gerado na elaboração; taxa de
  fail-closed da Etapa A (68 % dos 60 arquivos de maior fanout).

### Marco: validação completa antes da medição (2026-10-22)
- Suíte no `ci.yml` (Linux) **633 passed, 0 failed** (`fe95112`). Mutação em 6 grupos **125/125**,
  depois de pegar 1 sobrevivente real: `classification_review_status` trocado por uma constante.
- `auditor-prep` todo verde, inclusive `gen_tcb_roots --check` no fork. A allow-list do Mathlib,
  regenerada no CI, saiu **idêntica byte a byte** à commitada (run 39696176700).
- Primeiro run (PR #1) e 3 PRs de medição, todos abaixo de 300 s. Ainda não é steady-state: todo
  PR novo começava `cold` (D-61, abaixo). Relatórios com
  `classification_review_status: author-self-review` (L-26).

### Documentação (instrução 21)
- **L-27 emendada:** o caminho de sucesso da medição de fanout usa o arquivo de maior fanout cuja
  Etapa A não tem item não reconhecido ("sem sintaxe declarada" não basta). Arquivo escolhido:
  `Mathlib/Data/String/Defs.lean`.
- Pauta da Fase 1 (`roadmap.md`): 68 % dos 60 arquivos de maior fanout falham na Etapa A;
  `@[implemented_by]` gerado na elaboração (`WalkingParallelPair.ctorIdx`) derruba declarações pela L-5.
- **Correção do relatório da instrução 20:** as 10 `Não resolvida` do PR médio (#6) não são por
  sintaxe declarada (o arquivo não tem item não reconhecido). São 8 por `set_option backward.*`
  fora da política e 2 só por `implemented_by_candidate`; idênticas às do PR #3.
- `maintenance.md`: teste de referência para workflows que salvam cache (apagar, re-rodar vermelho,
  re-rodar, re-aquecer).

### Workflows e `auditor-ci` (instrução 20)
- **D-61: novo workflow reutilizável `auditor-warm-cache`** (modelo
  `ci/templates/auditor-warm-cache.yml`, disparado por `workflow_dispatch` e push no branch base).
  Salva no branch base os caches do inspetor e do Mathlib, com as mesmas chaves do `auditor-tier1`.
  Um PR só lê cache do próprio ref ou do base; sem isso, todo PR novo começava `cold`.
- **`auditor-ci inspector [--project .] [--check] [--github-output]`:** compila o inspetor sem
  auditar nada; com `--check`, só informa se está pronto (`built=true|false`). Exit 2 se não foi
  possível ter o inspetor.
- **A2: o `auditor-tier1` salva o cache do inspetor mesmo com o job vermelho**, desde que o build
  tenha terminado (`actions/cache/restore` + `actions/cache/save` com `always()`). Antes, um PR que
  saía `unresolved` nunca aquecia o próprio cache.
- **D-62: o checkout do auditor sai do workspace depois de instalado** (`$RUNNER_TEMP/auditor-tool`).
  Antes, todo relatório do CI saía com `project_dirty: true`. A política default passa a ser lida
  de `$RUNNER_TEMP/auditor-tool/policy.toml`.

### Marco: primeiro resultado ponta a ponta (2026-10-21)
- **Teste de fumaça da camada 2 aprovado.** No fork `Enzo47961/mathlib4` (`auditor-base` sobre o
  Mathlib `e1b2403b`), no GitHub Actions, `Mathlib/Logic/Hydra.lean` saiu com 20 de 20 declarações
  `Validada`/`Conforme`/`verified`, `exit_code` 0, nenhum item não reconhecido, com a allow-list do
  Mathlib sem comandos sem classificação (run 39680033069, auditor `6568835`). É o primeiro
  resultado ponta a ponta do projeto num arquivo real do Mathlib.
- **Estado da validação (referência para os PRs de medição):** suíte no `ci.yml` (Linux) 609 passed,
  0 failed (`e6e9f62`); mutação em 6 grupos 118/118 detectadas, 0 sobreviventes, 0 puladas.
- **Classificação dos comandos do Mathlib: auto-revisão (L-26).** Os relatórios declaram
  `classification_review_status: author-self-review`.

### Incompatível
- **Toolchain fixado: `leanprover/lean4:v4.22.0` → `leanprover/lean4:v4.36.0-rc1`** (a versão do
  Mathlib `master` em 2026-10-20, commit `e1b2403b`; instrução 12, opção X). A allow-list do
  core da v4.22.0 foi removida: projeto com outro toolchain → `allowlist_unavailable`
  (fail-closed). Inspetor `4`; classificação de comandos `4`.
- **`auditor check --timeout` removido** (D-36 rejeitada). O timeout por arquivo é só
  `--timeout-file`.
- **`auditor-ci run --budget` → `--timeout-total`**, e `--first-run-budget` →
  `--timeout-total-first-run`. Entradas do workflow reutilizável: `budget-seconds` →
  `timeout-total-seconds`, `first-run-budget-seconds` → `timeout-total-first-run-seconds`.
  Os nomes agora dizem o que medem: total do PR (`--timeout-total`) e por arquivo
  (`--timeout-file`).
  - `--timeout-total` (300 s) é **o** orçamento do PR: o SLA de 5 min, declarado para o
    steady-state (`cache_state` `warm`/`delta`).
  - `--timeout-total-first-run` (900 s) **não é um segundo orçamento permanente**. É o
    orçamento estendido de um run com cache frio (`cache_state: cold`), que acontece no
    primeiro run do fork ou depois de o cache ser despejado. Só vale com evidência positiva
    de cache frio, e o run declara `first_run: true`. Um run que passa dos 300 s dentro dele
    não falha: ganha `cache_cold_extension: true` e o label `auditor-first-run` (D-28;
    `docs/ci.md`; `docs/maintenance.md`, "Orçamentos de tempo do CI").
- **`native_decide` nunca sai `verified` na Fase 0** (Q9, opção a; D-43 confirmada). O
  axioma auxiliar que a v4.36 cria por uso (`<dona>._native.<tática>.ax_…`) deixa as premissas
  `Não resolvido` (`native_auxiliary_axiom`). A justificativa O-1 continua obrigatória (sem ela,
  `Não conforme`), mas não basta.
- **Raízes de TCB do toolchain viram `target_trusted_roots`** (D-42, D-47). Antes eram todos
  os `.olean` de primeiro nível do toolchain. Agora são só as raízes que o projeto-alvo de fato
  usa, medidas no fecho de imports do Mathlib no commit fixado (`e1b2403b`, conferido contra o
  `lake-manifest.json`): `Init`, `Lake`, `Lean` e `Std`. `LakeMain`, `Leanc`, `LeanChecker`,
  `LeanExport` e `LeanIR` deixam de ser TCB: um `@[extern]`/`@[implemented_by]` delas sai
  `unresolved`. Arquivo: `src/auditor/data/target_trusted_roots/` ("raízes cujos módulos são
  implicitamente confiáveis no fecho do projeto-alvo", não "todas as raízes da TCB do Lean");
  gerador: `tools/gen_tcb_roots.py`. No relatório da Etapa B, `boundary.toolchain_roots` virou
  `boundary.trusted_roots`, e `boundary.declared_roots` traz tudo o que o toolchain declara.
  Projeto-alvo que não é o Mathlib gera o próprio arquivo (L-21).

- **Allow-list de projeto: só as bibliotecas-alvo** (D-52). `auditor-gen-allowlist` extrai os
  comandos só das `lean_lib` marcadas `@[default_target]` no lakefile (ou das indicadas com
  `--lib`, repetível), e não mais de todo `.olean` do build. Sem nenhuma, erro (exit 2). O
  arquivo gerado ganhou o campo `libraries`. Motivo: no Mathlib, o `lake exe cache get` compila a
  biblioteca `Cache`, que define `Lean.Name.fromComponents` como `Mathlib.Lean.Name`; as duas não
  podem ser importadas juntas, e o gerador falhava. `generator_version` `2` → `3`.
- **Fim de linha normalizado nos hashes do `lake-manifest.json`** (D-53). `env_pin` (allow-list
  de projeto), `tools/gen_tcb_roots.py` e `tools/layer2/fanout.py` calculam o hash com CRLF → LF:
  o mesmo commit dá o mesmo valor num clone Windows (`core.autocrlf=true`) e no Linux. SHA-256 do
  conteúdo normalizado, não o hash de blob do git (SHA-1, D-18). `ENV_PIN_VERSION` `1` → `2`:
  allow-lists de projeto geradas antes ficam `allowlist_stale` e precisam ser regeneradas.
  `target_trusted_roots` regenerado: `lake_manifest_sha256` `c9b51d72…` (clone CRLF) →
  `f77f47db…` (o do repositório); o resto é idêntico.
- **`gen_tcb_roots.py --check` aceita fork de medição** (D-54, L-24): `HEAD` ≠ commit gravado só
  se o commit gravado for ancestral e a árvore só diferir em `.github/`, sem nenhum `.lean`.
- **Runner fixado: `ubuntu-24.04`** (D-55) no workflow reutilizável, no `ci.yml` e nos templates
  `auditor-label`/`auditor-report`. O GitHub migra `ubuntu-latest` para o Ubuntu 26 desde
  2026-10-19, e a medição da camada 2 não pode trocar de imagem no meio. A atualização das actions
  fixadas (Node 20, que o GitHub já força a rodar em Node 24) fica para uma rodada separada, fora
  da camada 2, com registro aqui.

- **Etapa A: `module` de cabeçalho e comandos-símbolo** (D-56, D-57; `stage_a_version` `2`).
  `module` (sistema de módulos da v4.36, primeira linha de todo arquivo do Mathlib) é aceito como
  primeiro token do arquivo; em outra posição, continua `unknown_command`. Os comandos de risco
  cujo token é símbolo (`?`, `$`) só são procurados no início de comando: antes, todo `?_` de
  `refine ⟨?_, ?_⟩` virava `syntax_extension_declared`. Palavras reservadas (`macro`, `#eval`, …)
  continuam detectadas em qualquer posição. Fixture de conformidade novo: `07-module-header`.

- **Relatório: schema `1.1.0`, campo obrigatório `tcb.classification_review_status`** (L-26).
  Classificação de projeto (`.auditor/classification.toml`) passa a exigir `reviewed_by` e
  `reviewer_independence` coerentes (`revision_note` opcional); sem eles, `auditor-gen-allowlist`
  sai com exit 2. A allow-list gerada ganha `classification_review` (`generator_version` `4`). O
  SHA-256 da classificação usa fim de linha normalizado, como o do manifesto (D-53).
- **`gen_tcb_roots.py --check` em fork aceita também `.auditor/`** (D-59, L-24): a allow-list e a
  classificação que o passo 3 do checklist commita no fork. Continua: nenhum `.lean`, ancestralidade.

### Caminhos do Mathlib que mudaram
- **`Mathlib/Logic/Basic.lean` não existe mais** no commit fixado (`e1b2403b`). O equivalente é
  `Mathlib/Basic/Logic/Basic.lean` (8072 dependentes, posição 24 no fanout). Nenhum script,
  fixture ou teste do auditor referencia o caminho antigo. Só `docs/ci.md` e o checklist da
  camada 2 o citavam, e os dois foram atualizados. As ferramentas da camada 2 (`fanout.py`)
  conferem o commit do checkout (`--expect-commit`), então não apontam para um arquivo de
  outro commit.
- **`auditor-ci-outcome/2`** (instrução 11): `exit_code`, `cache_state`, `first_run`,
  `cache_cold_extension`, relógio desde o trigger. A versão 1 é rejeitada pelo
  `label-decision` (resulta em `auditor-failed-infra`).

### Adicionado
- Timeout por arquivo (`--timeout-file`, 90 s) que encerra a auditoria do PR (exit 2).
- Orçamento wall-clock do PR desde o trigger, incluindo a preparação; `cache_state`;
  orçamento estendido com cache cold; label `auditor-first-run`.
- `tools/layer2/` (fanout e tempos por `cache_state`); `docs/layer2-checklist.md`.
- `fanout.py` registra a procedência (commit do checkout, SHA-256 do `lake-manifest.json`,
  `lean-toolchain`) e aceita `--expect-commit`. A saída JSON passou a ser
  `{"provenance": …, "rows": […]}`.
- `tools/layer2/native_usage.py`: proporção de declarações que usam avaliação nativa
  (`native_decide`, `+native`, `native := …`, `bv_decide`), contada com o lexer da Etapa A.
- Actions fixadas por SHA de commit; elan da release fixada com SHA-256 conferido.

### Segurança
- O inspetor importa o ambiente sem carregar extensões (`loadExts := false`): não executa
  código dos módulos importados, inclusive do PR (D-39).
- `unlock_limits` (novo na v4.36) é registrado pela Etapa A como os `set_option … 0` que aplica,
  e a política de `set_option` decide (D-41).
