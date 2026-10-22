# Relatório da Fase 0

```
phase_0_status: "closed at layer 1 + layer 2 measurement, pending steps 8-9"
```

**Atualização (2026-10-22, depois da instrução 22):** os passos 8 e 9 foram executados e a pendência da revisão externa foi respondida (seção "Condições"). A confirmação do fechamento incondicional é do revisor; até lá o status acima não muda.

Fechamento declarado pelo revisor na instrução 22 (2026-10-22), com duas condições antes de a Fase 1 abrir:

1. passos 8 (timeout / `auditor-failed-infra`) e 9 (`@auditor report` a pedido humano) do `docs/layer2-checklist.md`;
2. pendência da revisão externa descartada fechada: respondida, ou declarada como não respondida (`proposed-improvements.md`).

Depois dos passos 8 e 9, o revisor confirma o fechamento incondicional.

**Declaração obrigatória (L-26).** A classificação dos comandos do Mathlib que sustenta estes resultados foi elaborada e revisada pelo mesmo autor. Todo relatório desta fase declara `classification_review_status: author-self-review`. Qualquer apresentação externa destes resultados (Mathlib Zulip, artigo, blog post ou outra) deve qualificar que a classificação é auto-revisada. A Fase 1 inclui revisão independente antes de qualquer alegação de cobertura do Mathlib em contexto externo.

## Contexto

| Item | Valor |
|---|---|
| Auditor executado | `7f7238d69adcd3255e3693ddbe76a2cf3302dff4` (depois dele só mudou documentação) |
| Fork de medição | `Enzo47961/mathlib4`, `auditor-base` = `2efeeec` = Mathlib `e1b2403b` + só `.github/` e `.auditor/` |
| Toolchain | `leanprover/lean4:v4.36.0-rc1` |
| Runner | `ubuntu-24.04` (D-55) |

## Critérios de fechamento

| Critério | Estado | Evidência |
|---|---|---|
| 3 PRs `warm` abaixo de 5 min no caminho de sucesso (trivial, médio, fanout) | cumprido | #5 126,1 s · #6 129,7 s · #8 137,6 s |
| Sonda do fanout no caminho de sucesso `verified` | cumprido | PR #8: `auditor_probe_fanout_success` `verified`, 9/9 no arquivo |
| Caminho fail-closed reportado separadamente | cumprido | PR #7 (`Data/Set/Defs.lean`) |
| Todos os relatórios com `author-self-review` | cumprido | PRs #5–#8 e fumaça do `auditor-prep` |
| Todos os relatórios com `project_dirty: false` | cumprido | PRs #5–#8 e fumaça do `auditor-prep` (D-62) |
| L-27 emendada ("Etapa A limpa") | cumprido | `docs/limitations.md` |
| Esclarecimento do PR #6 | cumprido: (a) | erro de redação no relatório da instrução 20; sem bug na Etapa A |
| Passo 8 (timeout / `auditor-failed-infra`) | executado, passou | PR #9: `timeout_kind: file`, exit 2, `infra_failed: true`, job verde, PR mesclável, label `auditor-failed-infra`, nenhum comentário |
| Passo 9 (`@auditor report` a pedido humano) | executado; 1ª tentativa falhou (bug corrigido), 2ª passou | PR #8: um comentário "Pedido por um humano", sumário correto (`maintenance.md`) |
| Pendência da revisão externa descartada | respondida | outra IA sem acesso ao código-fonte (`proposed-improvements.md`) |

## Condições

- **Passo 8.** PR #9 (`l2-timeout-w`, `timeout-file-seconds: 5`, nunca para merge), run 39818035267: `Hydra.lean` `timeout` aos 5,54 s, `exit_code: 2`, `infra_failed: true`, `cache_state: warm`, job verde, `mergeable`, label `auditor-failed-infra`. Teste de referência em `maintenance.md`.
- **Passo 9.** A 1ª tentativa (run 39818084000) respondeu "nenhuma execução" para um commit auditado: o filtro `head_sha` da API do GitHub não é determinístico. Corrigido no modelo `auditor-report.yml` (auditor `7ba9b6f`, fork `465d97e`); a 2ª tentativa (run 39821013448) postou um único comentário correto. Não testado: comentário de quem não tem acesso (exigiria outra conta); a garantia é a condição `author_association`, travada por teste.
- **Revisão externa.** Outra IA, sem acesso ao código-fonte; diagnóstico e regras para a revisão independente da Fase 1 em `proposed-improvements.md`.
- **Validação depois da correção:** suíte 666 passed (`7ba9b6f`); mutação 138/138.

## Medição na camada 2

A distinção entre medição no caminho de sucesso e medição no caminho fail-closed é da arquitetura, não da ferramenta (L-27). Caminho de sucesso: arquivo que a Etapa A aceita inteiro. Caminho fail-closed: arquivo que a Etapa A recusa; nele `unresolved` é o resultado correto.

### Estado dos PRs do fork (todos abertos como evidência, nenhum para merge)

| PR | Branch | Arquivo | Caminho | Cache | Auditor | Total | Resultado |
|---|---|---|---|---|---|---|---|
| #1 | `l2-first-run` | `Logic/Hydra.lean` | sucesso | `cold`, `first_run` | `382b5a5` | 136,1 s | 20/20 `verified`, exit 0 |
| #2 | `l2-trivial` | `Logic/Hydra.lean` | sucesso | `cold`, `first_run` | `382b5a5` | 137,0 s | 20/20 `verified`, exit 0 |
| #3 | `l2-medio` | `Algebra/Homology/Embedding/Connect.lean` | sucesso (arquivo) | `cold`, `first_run` | `382b5a5` | 137,6 s | sonda `verified`; 29 `verified` / 10 `unresolved` |
| #4 | `l2-fanout` | `Data/Set/Defs.lean` | fail-closed | `cold`, `first_run` | `382b5a5` | 148,1 s | 37/37 `unresolved` (sintaxe declarada) |
| #5 | `l2-trivial-w` | `Logic/Hydra.lean` | sucesso | `warm` | `7f7238d` | 126,1 s | 20/20 `verified`, exit 0 |
| #6 | `l2-medio-w` | `Algebra/Homology/Embedding/Connect.lean` | sucesso (arquivo) | `warm` | `7f7238d` | 129,7 s | sonda `verified`; 29 `verified` / 10 `unresolved`; exit 1 |
| #7 | `l2-fanout-failclosed-w` | `Data/Set/Defs.lean` | fail-closed | `warm` | `7f7238d` | 142,1 s | 37/37 `unresolved` por `stage_a_unrecognized`; sonda `unresolved` (correto, L-17) |
| #8 | `l2-fanout-success-w` | `Data/String/Defs.lean` (posição 4, 8147 dependentes) | sucesso | `warm` | `7f7238d` | 137,6 s | sonda `verified`; 9/9 `verified`; exit 0 |
| #9 | `l2-timeout-w` | `Logic/Hydra.lean`, `timeout-file-seconds: 5` | passo 8 (infra) | `warm` | `7f7238d` | 119,3 s | `timeout`, exit 2, `infra_failed`, job verde, `auditor-failed-infra` |

Em #5–#8: `clock_origin: trigger`, `build_cache: hit`, `inspector: hit`, `project_dirty: false`, nenhum sinal de ambiente nem timeout.

**PR #6:** a Etapa A aceita o arquivo inteiro (nenhum item não reconhecido). As 10 `unresolved` são de declarações específicas, idênticas às do PR #3: 8 por `set_option backward.*` fora da política e 2 só por `implemented_by_candidate` (`CategoryTheory.Limits.WalkingParallelPair.ctorIdx`, atributo gerado na elaboração; ver `roadmap.md`).

**Orçamento:** 300 s; maior medição `warm`, 142,1 s. A preparação domina: no PR #5, checkout 33 s, `lake exe cache get` 63 s (mesmo com hit, desempacota os `.ltar`), auditoria 13 s. Observação para a Fase 1, não prioridade.

### Workflows de cache

- **D-61:** `auditor-warm-cache` salva no branch base os caches do inspetor e do Mathlib (run 39758479162).
- **A2:** o inspetor é salvo mesmo com job vermelho. Testado sem depender de hit (procedimento de referência em `maintenance.md`).
- **D-62:** o auditor sai do workspace depois de instalado; `project_dirty: false` em todos os relatórios.

## Validação

| Item | Resultado |
|---|---|
| Suíte (`ci.yml`, Linux) | 662 passed, 0 failed (runs 39758445713 sobre `7f7238d` e 39813452380 sobre `0c64a3e`) |
| Mutação | 6 grupos, 135/135 detectadas, 0 sobreviventes, 0 puladas (`maintenance.md`); 138/138 depois da correção do passo 9 |
| `auditor-prep` (run 39812801650) | verde; allow-list com 259 comandos, 0 sem classificação, 8651 módulos; `gen_tcb_roots --check` exit 0; fumaça 20/20, `project_dirty: false` |
| Allow-list do Mathlib | regenerada no CI, idêntica byte a byte à commitada (run 39696176700) |

## Limitações

L-1 a L-28 em `docs/limitations.md`. As que mais pesam na leitura destes resultados: L-1 e L-14 (kernel, compilador e inspetor na TCB), L-5 (`@[implemented_by]` é candidato), L-9 (correspondência não auditada), L-17 (o que a Etapa A não reconhece derruba o arquivo), L-25 e L-26 (classificação do Mathlib fail-closed nos ambíguos e auto-revisada), L-27 (caminho de sucesso e fail-closed separados), L-28 (0 usos reais de avaliação nativa em `Mathlib@e1b2403b`).

## Pauta da Fase 1

Prioridades P0 em `docs/roadmap.md`: `@[implemented_by]` gerado na elaboração e a taxa de fail-closed da Etapa A (68 % dos 60 arquivos de maior fanout). A pergunta de pesquisa da Fase 1 (se a hipótese semântica vale a pena) continua em aberto.
