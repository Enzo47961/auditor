# Integração CI (GitHub Actions)

## Peças

| Arquivo | Onde vive | Gatilho | Permissões | Executa código do PR? |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | este repositório | push, PR | leitura | — (testa o próprio auditor) |
| `.github/workflows/auditor-tier1.yml` | este repositório (reutilizável) | `workflow_call` | **leitura** | **sim** (`lake build`) |
| `ci/templates/auditor-tier1.yml` | repositório-alvo | `pull_request` em `**.lean` | leitura | sim, via o reutilizável |
| `ci/templates/auditor-label.yml` | repositório-alvo | `workflow_run` (auditor-tier1 concluído) | escrita em PRs/issues | **não** |
| `ci/templates/auditor-report.yml` | repositório-alvo | `issue_comment` (`@auditor report`) | escrita em PRs | **não** |

A lógica fica em `auditor-ci` (`src/auditor/ci.py`), testada em `tests/ci`. Os workflows só a chamam. A política de segurança dos workflows também é teste (`tests/ci/test_workflows.py`): sem `pull_request_target`, permissões mínimas, nenhum checkout nos workflows com escrita, nenhuma interpolação de texto do PR em scripts, actions fixadas por SHA de commit, elan da release fixada com SHA-256 conferido. Os 5 arquivos passam no `actionlint` 1.7.12.

## Comportamento (spec, componente 7; instrução 11)

- **Roda em todo PR que toca `.lean`**: o modelo filtra por `paths: ["**.lean"]`, e o job audita os arquivos `.lean` alterados entre base e head que ainda existem.
- **Orçamento do PR = wall-clock do trigger até o relatório (D-28).** O relógio começa no evento do PR (`github.event.pull_request.updated_at`; numa re-execução, no início do job) e **inclui a preparação**: instalação, `lake exe cache get` e compilação do inspetor. O `outcome.json` declara `clock_origin`, `setup_elapsed_s`, `audit_elapsed_s` e `elapsed_s`.
  - **Steady-state (`cache_state` `warm` ou `delta`): 5 min** (`timeout-total-seconds`; `auditor-ci run --timeout-total`; padrão 300).
  - **Cache `cold`: orçamento estendido** (`timeout-total-first-run-seconds`; `--timeout-total-first-run`; padrão 900) e `first_run: true`. Se a auditoria passar dos 5 min sem estourar o estendido, o PR **não falha**: `cache_cold_extension: true` e label `auditor-first-run` (diferente de `auditor-failed-infra`). O SLA de 5 min é declarado como steady-state.
- **`cache_state`** vem de dois sinais medidos, nunca de suposição:
  - cache de build do alvo (`~/.cache/mathlib`, restaurado por `actions/cache/restore`): `hit` (chave exata: mesmo commit base), `partial` (só `restore-keys`), `miss`, ou `none` (alvo sem `cache-get`);
  - binário do inspetor no cache local (`hit`/`miss`, medido pelo `auditor-ci`).
  - Regra: `cold` se o cache de build é `miss` ou o inspetor é `miss`; `delta` se o cache de build é `partial`; senão `warm`. **O orçamento estendido só é concedido com evidência positiva de cache frio**: sinal ausente conta como quente.
- **Timeout por arquivo (D-21): 90 s** (`timeout-file-seconds`; `auditor check --timeout-file`). Cada arquivo recebe o menor entre o timeout por arquivo e o que resta do orçamento. Arquivo que estoura o timeout **encerra a auditoria do PR**: os arquivos seguintes ficam `not_audited_after_timeout` e o PR sai com **exit 2**. Arquivo que já não cabe no orçamento é `skipped_budget`. O inspetor é compilado antes do primeiro arquivo, para não consumir o timeout de um arquivo.
- **Exit code do PR** (`auditor-ci run`, mesmos códigos da CLI): 0 tudo verificado; 1 rejeição ou não resolução; 2 infraestrutura (orçamento, timeout, exit 2 de algum arquivo). Infraestrutura vence: um PR com uma rejeição e um timeout sai com 2, e `audit_failed` continua `true`.
- **Resultado no GitHub:**
  - infraestrutura (exit 2, relatório ilegível, job cancelado ou sem resultado): o job **não falha por isso**, portanto não bloqueia merge; o workflow de label aplica `auditor-failed-infra`, que exige revisão humana explícita; timeout nunca é sucesso;
  - rejeição ou não resolução (`audit_failed`): um passo dedicado falha o job. Se o check é obrigatório é configuração do repositório-alvo (D-22).
- **Sumário** no Job Summary, com o aviso "Correspondência: Não Auditada", `cache_state`, tempos (preparação, auditoria, total) e p95 por arquivo. **Relatórios completos** no artefato `auditor-report`, junto com `outcome.json` (formato `auditor-ci-outcome/2`) e `summary.md`.
- **Comentário no PR só a pedido humano:** um comentário cuja primeira linha começa com `@auditor report`, de OWNER, MEMBER ou COLLABORATOR, publica o sumário da última execução para o commit atual. O sistema nunca comenta por iniciativa própria.
- **Cache do inspetor (D-7):** `actions/cache` em `~/.cache/auditor`, chave por ref do auditor + `lean-toolchain`. O Job Summary registra, por arquivo, se o binário estava em cache (`hit`/`miss`).
- **Fixação de versões (D-25, obrigatória):** toda action por SHA de commit, com a versão num comentário; elan baixado da release `v4.2.4` e conferido por SHA-256. O `elan-init.sh` não é usado: mesmo tirado de uma tag, ele baixa a release `latest` do elan. Procedimento de atualização em `docs/maintenance.md`.

### Por que três workflows (D-24)

PRs do Mathlib frequentemente vêm de forks. O job que audita precisa compilar o código do PR (`lake build`), e código não confiável **nunca** roda com token de escrita (o padrão `pull_request_target` + checkout do PR é uma vulnerabilidade conhecida). Por isso:
- a auditoria roda em `pull_request`, com token só de leitura, e não aplica label nem comenta;
- o label é aplicado por `workflow_run`, que roda no contexto confiável do repositório, nunca faz checkout e trata o artefato do job auditado como dado não confiável (`auditor-ci label-decision` lê só os booleanos `infra_failed` e `cache_cold_extension`, com checagem estrita de tipo; qualquer desvio resulta em `auditor-failed-infra`, fail-closed);
- o comentário é disparado por `issue_comment`, também sem checkout.

## Instalação no fork do Mathlib (camada 2)

1. Fixar o auditor num commit: `AUDITOR_SHA`.
   - **Toolchain:** o auditor traz allow-list do core só para o toolchain fixado (`src/auditor/data/allowlist/`; hoje, `leanprover/lean4:v4.36.0-rc1`, o do Mathlib `master` no commit `e1b2403b`). A base dos PRs de medição precisa usar esse toolchain. Se o Mathlib subir de versão antes da medição, há duas saídas: fixar o fork no commit `e1b2403b` (ou outro com o mesmo `lean-toolchain`), ou subir o toolchain do auditor de novo (`docs/maintenance.md`). Com outro toolchain, todo arquivo sai `allowlist_unavailable` (fail-closed).
2. Copiar `ci/templates/*.yml` para `.github/workflows/` do fork e substituir `OWNER/auditor` e `AUDITOR_SHA`.
3. Gerar e versionar a allow-list do Mathlib: `auditor-gen-allowlist --project .` depois de `lake exe cache get`, e classificar os comandos em `.auditor/classification.toml` (ver `docs/maintenance.md`). Sem ela, todo arquivo do Mathlib sai `Não resolvida` por `unknown_command`.
4. Fazer o **primeiro run** (cache cold): um PR qualquer que toque um `.lean`. Ele declara `first_run: true` e popula os caches. Não é medição de steady-state.
5. Abrir os PRs de medição, **depois** do primeiro run.

## Escolha do arquivo de maior fanout (D-38)

`tools/layer2/fanout.py <projeto> --root Mathlib` ordena os módulos do projeto por fanout.

**(a) Como é calculado.**
1. Lista os `.lean` sob `<projeto>/<root>/` e `<projeto>/<root>.lean`; o nome do módulo é o caminho relativo com `/` → `.`.
2. Lê só o **cabeçalho** de cada arquivo: linhas em branco, comentários de linha (`--`) e de bloco (`/- … -/`, com aninhamento), `prelude`, `module` e linhas `import` (com os modificadores `public`, `meta`, `private`; vários módulos por linha). O primeiro comando de outro tipo encerra o cabeçalho, como no Lean. Nome de módulo ilegível (ex.: com `«»`) ou comentário de bloco dentro de uma linha `import` é erro (exit 2), nunca ignorado.
3. Monta o grafo de imports **restrito ao projeto**: imports de fora (`Init`, `Std`, `Lean`, dependências) são descartados.
4. Inverte as arestas e calcula, por busca em largura, para cada módulo:
   - `direct`: quantos módulos o importam diretamente;
   - `transitive`: quantos módulos dependem dele direta ou transitivamente (fecho reverso);
   - `imports_transitive`: quantos módulos do projeto ele mesmo importa, direta ou transitivamente (fecho direto).
5. Ordena por `transitive` decrescente, depois `direct` decrescente, depois nome. Determinístico.

Não há peso por uso: uma aresta é um `import`, não uma referência a constante.

**(b) Por que essa definição.**
- O fanout reverso transitivo é a medida de "raio de invalidação": mudar o módulo invalida o `.olean` de todos os dependentes. No Mathlib, isso decide quanto do cache do `lake exe cache get` deixa de corresponder ao commit do PR. Se isso pesa no tempo é **hipótese a medir**, não fato: o `lake build` do módulo-alvo só precisa dos módulos que ele importa, não dos dependentes; o efeito esperado está na preparação (`cache get`), que o orçamento de 5 min passou a incluir (D-28).
- Restringir ao projeto e usar só o cabeçalho torna a ferramenta barata (não precisa compilar nada nem carregar `.olean`) e reprodutível a partir do checkout.
- Peso por uso (contar referências a constantes) exigiria o ambiente elaborado de todo o Mathlib e mediria outra coisa: o quanto as provas dependem do módulo, não o quanto do build é invalidado. Fica fora.
- **Ressalva, para a medição não ser mal lida:** o custo da **auditoria** de um arquivo (o `lake build` do módulo-alvo e a leitura do ambiente pelo inspetor) cresce com o fecho **direto** (`imports_transitive`), não com o fanout. Um arquivo de fanout máximo tende a estar na base da hierarquia, com fecho direto pequeno. Por isso a ferramenta também imprime `imports_transitive`; o arquivo "médio" ou um quarto PR pode ser escolhido pelo maior fecho direto, se o revisor quiser medir o pior caso da auditoria em si.

**(c) Como é testado** (`tests/maintenance/test_layer2_tools.py`):
- cabeçalho: comentários aninhados, `module`, `public import`, vários módulos por linha, comentário no fim da linha, parada no primeiro comando (um `import` depois de um `theorem` não conta);
- nome ilegível → erro;
- grafo sintético de 5 módulos com dependência transitiva, import externo descartado e módulo raiz: valores exatos de `direct`, `transitive` e `imports_transitive` e a ordem do ranking.

## Evidência pendente (camada 2): roteiro

A Fase 0 só fecha com esta evidência. A Fase 1 não começa antes dela.

| Item da DoD | Como produzir |
|---|---|
| Primeiro run no fork | PR qualquer; registrar `cache_state` (`cold` esperado), `first_run`, `elapsed_s` e se houve `cache_cold_extension` |
| 3 PRs de medição no steady-state | **trivial** (ex.: docstring num arquivo folha), **médio** (um lema novo num arquivo de tamanho típico), **arquivo de maior fanout**, escolhido mecanicamente com `python tools/layer2/fanout.py <fork> --root Mathlib` (anexar a tabela; não só `Mathlib/Logic/Basic.lean`) |
| Tempos por `cache_state` | baixar o artefato `auditor-report` de cada execução e rodar `python tools/layer2/timings.py <diretórios>`: total, preparação, auditoria e p95 por arquivo, separados por `cold`/`delta`/`warm` |
| Caminho de timeout (`auditor-failed-infra`, sem bloquear) | PR com `timeout-file-seconds` artificial pequeno (ex.: 5): o PR sai com exit 2, o job fica verde e o PR recebe o label |
| Action integrada e testada em fork | os itens acima + um `@auditor report` de um colaborador |
| Reajuste do timeout por arquivo | p95 por arquivo medido; o default de 90 s é reajustado com dados, não com intuição |
| Verificações de premissa | o carimbo `updated_at` do evento coincide com o push (comparar com o horário do commit); o tamanho de `~/.cache/mathlib` cabe no limite de cache do repositório |

Trazer: os 3 relatórios (`outcome.json` + `summary.md`), a tabela do `timings.py` e a do `fanout.py`.

O comportamento de timeout/label/não bloqueio/first run já está testado na camada 1 (`tests/ci/test_ci.py`), com tempos artificiais.
