# Changelog

Mudanças que afetam quem usa o auditor (CLI, `auditor-ci`, workflows, relatório). A Fase 0
ainda não está em produção (a camada 2 não começou), então mudanças incompatíveis são feitas
sem período de transição.

## Não lançado

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
