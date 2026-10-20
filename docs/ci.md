# Integração CI (GitHub Actions)

## Peças

| Arquivo | Onde vive | Gatilho | Permissões | Executa código do PR? |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | este repositório | push, PR | leitura | — (testa o próprio auditor) |
| `.github/workflows/auditor-tier1.yml` | este repositório (reutilizável) | `workflow_call` | **leitura** | **sim** (`lake build`) |
| `ci/templates/auditor-tier1.yml` | repositório-alvo | `pull_request` em `**.lean` | leitura | sim, via o reutilizável |
| `ci/templates/auditor-label.yml` | repositório-alvo | `workflow_run` (auditor-tier1 concluído) | escrita em PRs/issues | **não** |
| `ci/templates/auditor-report.yml` | repositório-alvo | `issue_comment` (`@auditor report`) | escrita em PRs | **não** |

A lógica fica em `auditor-ci` (`src/auditor/ci.py`), testada em `tests/ci`. Os workflows só a chamam. A política de segurança dos workflows também é teste (`tests/ci/test_workflows.py`): sem `pull_request_target`, permissões mínimas, nenhum checkout nos workflows com escrita, nenhuma interpolação de texto do PR em scripts, ações com versão fixada. Os 5 arquivos passam no `actionlint` 1.7.12.

## Comportamento (spec, componente 7)

- **Roda em todo PR que toca `.lean`**: o modelo filtra por `paths: ["**.lean"]`, e o job audita os arquivos `.lean` alterados entre base e head que ainda existem.
- **Orçamento de 5 min** (`budget-seconds`, padrão 300) para a auditoria de todos os arquivos. Cada arquivo recebe como timeout o que resta do orçamento. Arquivo que não cabe no orçamento é `skipped_budget`.
- **Falha de infraestrutura** (orçamento esgotado, timeout, exit 2, relatório ilegível, job cancelado ou sem resultado):
  - o job **não falha**, portanto não bloqueia merge;
  - o workflow de label aplica `auditor-failed-infra`, que exige revisão humana explícita;
  - timeout nunca é sucesso.
- **Rejeição ou não resolução** (exit 1 em algum arquivo): o job falha. Se o check é obrigatório é configuração do repositório-alvo (D-22).
- **Sumário** no Job Summary, com o aviso "Correspondência: Não Auditada". **Relatórios completos** no artefato `auditor-report`, junto com `outcome.json` e `summary.md`.
- **Comentário no PR só a pedido humano:** um comentário cuja primeira linha começa com `@auditor report`, de OWNER, MEMBER ou COLLABORATOR, publica o sumário da última execução para o commit atual. O sistema nunca comenta por iniciativa própria.
- **Cache do inspetor (D-7):** `actions/cache` em `~/.cache/auditor`, chave por ref do auditor + `lean-toolchain`. O Job Summary registra se o cache foi restaurado e, por arquivo, se o binário estava em cache (`hit`/`miss`). A taxa de acerto vem dessas linhas, acumuladas entre execuções.

### Por que três workflows (D-24)

PRs do Mathlib frequentemente vêm de forks. O job que audita precisa compilar o código do PR (`lake build`), e código não confiável **nunca** roda com token de escrita (o padrão `pull_request_target` + checkout do PR é uma vulnerabilidade conhecida). Por isso:
- a auditoria roda em `pull_request`, com token só de leitura, e não aplica label nem comenta;
- o label é aplicado por `workflow_run`, que roda no contexto confiável do repositório, nunca faz checkout e trata o artefato do job auditado como dado não confiável (`auditor-ci label-decision` lê só o booleano `infra_failed`, com checagem estrita de tipo; qualquer desvio resulta em label, fail-closed);
- o comentário é disparado por `issue_comment`, também sem checkout.

## Instalação no fork do Mathlib (camada 2)

1. Fixar o auditor num commit: `AUDITOR_SHA`.
2. Copiar `ci/templates/*.yml` para `.github/workflows/` do fork e substituir `OWNER/auditor` e `AUDITOR_SHA`.
3. Gerar e versionar a allow-list do Mathlib: `auditor-gen-allowlist --project .` depois de `lake exe cache get`, e classificar os comandos em `.auditor/classification.toml` (ver `docs/maintenance.md`). Sem ela, todo arquivo do Mathlib sai `Não resolvida` por `unknown_command`.
4. Abrir os PRs de medição.

## Evidência pendente (camada 2): roteiro

| Item da DoD | Como produzir |
|---|---|
| CLI em 3 PRs reais (trivial, médio, núcleo `Mathlib/Logic/Basic.lean`) + arquivo de maior fanout, com tempos | PRs no fork; registrar `elapsed_s` do `outcome.json` e a duração do job. Escolher o arquivo de maior fanout por contagem de dependentes (`lake` + grep de imports) e documentar a escolha |
| Caminho de timeout (`auditor-failed-infra`, sem bloquear) | PR com `budget-seconds` artificial pequeno (ex.: 5). O relatório declara `timeout_test`, o job fica verde e o PR recebe o label |
| Action integrada e testada em fork | os itens acima + um `@auditor report` de um colaborador |
| Taxa de acerto do cache do inspetor (D-7) | linhas "cache do inspetor" do Job Summary em várias execuções |

O comportamento de timeout/label/não bloqueio já está testado na camada 1 (`tests/ci/test_ci.py`), com orçamento artificial.
