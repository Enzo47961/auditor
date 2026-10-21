# Changelog

Mudanças que afetam quem usa o auditor (CLI, `auditor-ci`, workflows, relatório). A Fase 0
ainda não está em produção (a camada 2 não começou), então mudanças incompatíveis são feitas
sem período de transição.

## Não lançado

### Incompatível
- **Toolchain fixado: `leanprover/lean4:v4.22.0` → `leanprover/lean4:v4.36.0-rc1`** (a versão do
  Mathlib `master` em 2026-10-20, commit `e1b2403b`; instrução 12, opção X). A allow-list do
  core da v4.22.0 foi removida: projeto com outro toolchain → `allowlist_unavailable`
  (fail-closed). Inspetor `3`; classificação de comandos `4`.
- **`auditor check --timeout` removido** (D-36 rejeitada). O timeout por arquivo é só
  `--timeout-file`.
- **`auditor-ci run --budget` → `--timeout-total`**, e `--first-run-budget` →
  `--timeout-total-first-run`. Entradas do workflow reutilizável: `budget-seconds` →
  `timeout-total-seconds`, `first-run-budget-seconds` → `timeout-total-first-run-seconds`.
  Os nomes agora dizem o que medem: total do PR (`--timeout-total`) e por arquivo
  (`--timeout-file`).
- **`auditor-ci-outcome/2`** (instrução 11): `exit_code`, `cache_state`, `first_run`,
  `cache_cold_extension`, relógio desde o trigger. A versão 1 é rejeitada pelo
  `label-decision` (resulta em `auditor-failed-infra`).

### Adicionado
- Timeout por arquivo (`--timeout-file`, 90 s) que encerra a auditoria do PR (exit 2).
- Orçamento wall-clock do PR desde o trigger, incluindo a preparação; `cache_state`;
  orçamento estendido com cache cold; label `auditor-first-run`.
- `tools/layer2/` (fanout e tempos por `cache_state`); `docs/layer2-checklist.md`.
- Actions fixadas por SHA de commit; elan da release fixada com SHA-256 conferido.

### Segurança
- O inspetor importa o ambiente sem carregar extensões (`loadExts := false`): não executa
  código dos módulos importados, inclusive do PR (D-39).
- `unlock_limits` (novo na v4.36) é registrado pela Etapa A como os `set_option … 0` que aplica,
  e a política de `set_option` decide (D-41).
