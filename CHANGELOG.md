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
- **Raízes de TCB do toolchain viram allow-list** (D-42, condição do revisor). Antes eram todos
  os `.olean` de primeiro nível do toolchain. Agora são só as raízes que o projeto-alvo de fato
  usa, medidas no fecho de imports do Mathlib no commit fixado (`e1b2403b`, conferido contra o
  `lake-manifest.json`): `Init`, `Lake`, `Lean` e `Std`. `LakeMain`, `Leanc`, `LeanChecker`,
  `LeanExport` e `LeanIR` deixam de ser TCB: um `@[extern]`/`@[implemented_by]` delas sai
  `unresolved`. Arquivo: `src/auditor/data/tcb_roots/`; gerador: `tools/gen_tcb_roots.py`.

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
