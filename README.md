# auditor — verificador mecânico de integridade de provas Lean 4 (Fase 0, Tier 1)

## O que esta ferramenta NÃO faz

Leia esta seção antes de qualquer outra. Um selo emitido por esta ferramenta **não** significa "a prova está correta" nem "o teorema diz o que o autor afirma".

> **Declaração obrigatória (L-26): `classification_review_status: author-self-review`.** A classificação dos comandos do Mathlib que sustenta os resultados desta ferramenta foi elaborada e revisada pelo mesmo autor; não houve revisão independente. Todo relatório, sumário e comentário declara isso. Nenhum resultado de cobertura do Mathlib pode ser apresentado a terceiros (Mathlib Zulip, artigo, blog ou outro) sem essa qualificação. A revisão independente é item da Fase 1 (`docs/roadmap.md`).

- **Não audita correspondência.** Não verifica se o enunciado formal corresponde ao enunciado informal (artigo, LaTeX, intenção do autor). Todo relatório da Fase 0 declara `correspondence_status: "Não auditada"`, sem exceção. Um teorema que prova a coisa errada recebe o mesmo selo que um que prova a coisa certa.
- **Não audita o kernel do Lean.** O kernel é âncora de confiança (TCB), não objeto auditado. Um bug no kernel invalida todos os selos e esta ferramenta não o detectaria.
- **Não usa LLM**, em nenhuma capacidade, em nenhum ponto do código.
- **Não faz análise semântica de provas**: não decompõe táticas em obrigações, não detecta circularidade semântica, não avalia se hipóteses são vazias ou contraditórias.
- **Não procura contraexemplos**, não tenta refutar, não usa SMT.
- **Não lê LaTeX nem PDF.**
- **Não distingue contextos construtivos.** `Classical.choice` é permitido por padrão; isso é decisão explícita da Fase 0, não omissão.
- **Não opera como bot.** Não abre PRs, não comenta em PRs por iniciativa própria, não age sob identidade própria. Tudo que aparece num PR foi pedido por um humano (ver [Integração CI](#integração-ci)).
- **Não revoga selos.** O modelo de revogação está documentado em `docs/invalidation.md`; a implementação é Fase 1.
- **Não garante cobertura sintática completa na Etapa A.** A Etapa A é varredura léxica, não parsing fiel (ver [Limitações](#limitações)). A Etapa B, que inspeciona declarações elaboradas, é a fonte de evidência; a Etapa A só sinaliza candidatos.
- **Não emite veredito binário.** A saída é um mapa de dívida epistêmica: três estados ortogonais por declaração, mais a lista do que não foi verificado.

## Status

**Fase 0 = closed unconditionally 2026-10-22. Fase 1 = em andamento (sub-fase 1a: P0-1 e P0-2; `docs/p0-1-implemented-by.md`, `docs/p0-2-fail-closed.md`).**

Fechamento confirmado pelo revisor na instrução 24: auditor `69ed9cf`, fork `auditor-base` `018d7db`, 674 testes, 141/141 mutações, passos 8 e 9 da camada 2 (o 9 com sumário qualificado), L-26 declarada em todos os artefatos. Evidência em `docs/phase0-report.md`. A Fase 1 começa pelos dois P0 de `docs/roadmap.md`.

As tabelas abaixo registram como as duas camadas da Fase 0 foram construídas. O critério de go/no-go foi a camada 2 (GitHub Actions em PRs reais do fork do Mathlib), não a camada 1.

**Camada 1 — done no ambiente do builder.** Itens verificáveis sem Mathlib, com evidência produzida no ambiente de desenvolvimento. Toolchain fixado: **`leanprover/lean4:v4.36.0-rc1`** (o do Mathlib `master`, instrução 12). **Q9 decidida (instrução 13):** `native_decide` nunca sai `verified` na Fase 0 (fail-closed permanente; reavaliação pelo kernel é pesquisa da Fase 1).

| Item | Estado |
|---|---|
| README com limitações e seção "O que NÃO faz" | em revisão |
| Conformance suite (5 cenários obrigatórios + `04b-extern` + `06-tcb-boundary`) passa | **verde** fim a fim (CLI real, Lean real) |
| Fail-closed suite (3 cenários) passa | **verde**: macro customizada e zero-width → `Não resolvida` (Etapa A); ciclo de imports → `compile_failure`, exit 1 |
| Etapa A (pré-scan léxico) | feita: 39 testes, 9 mutações detectadas; D-1 com `#reduce`/`#guard`/`#widget` |
| Gerador de allow-list testado contra projeto Lake arbitrário (Q5) | feito: 16 testes, 9 mutações detectadas |
| Etapa B (inspetor Lean v2 + wrapper) | feita: 13 mutações detectadas (rodada anterior) |
| Fronteira de TCB (Q7-a) | feita: algoritmo em `docs/tcb.md`, 19 testes unitários, canário `06-tcb-boundary` |
| Policy engine (`policy.toml` + regras com regressão própria) | feito: 30 mutações detectadas (política, agregador, relatório, fronteira, fingerprint) |
| Schema JSON v1 publicado e validado | feito: `schema/report-v1.json`; todo relatório dos fixtures valida; o schema rejeita 8 violações de princípio |
| CLI (`auditor check`) com exit codes Q6 e `overall_status` Q4 | feita |
| `docs/tcb.md` | feito, com a seção "Fronteira de TCB" |
| `docs/invalidation.md` (só modelo) | feito: selos imutáveis, eventos append-only, estado derivado, propagação |
| `docs/limitations.md`, `docs/maintenance.md` | feito |
| Nenhuma dependência de LLM (verificação automatizada) | feito: `tests/maintenance/test_no_llm.py` |
| GitHub Action (workflow reutilizável + modelos para o fork) | feita e testada na camada 1: 78 testes (`tests/ci`), `actionlint` sem apontamentos; actions fixadas por SHA, elan por release + SHA-256; orçamento wall-clock do PR com `cache_state`, timeout por arquivo de 90 s. Teste em fork é camada 2 |
| Testes de mutação versionados (`tools/mutation`) | catálogo de 84 mutações em 5 grupos, com teste de integridade do catálogo |
| Nenhuma promessa não cumprida no README | pendente (revisão final) |

**Camada 2 — done no ambiente real** (evidência em `docs/phase0-report.md`).

| Item | Estado |
|---|---|
| Allow-list do Mathlib gerada no fork (`auditor-gen-allowlist --project`), com os comandos do Mathlib classificados | feito: 259 comandos, 0 sem classificação; regenerada no CI idêntica byte a byte (run 39696176700) |
| Primeiro run no fork (cache cold, `first_run: true`) | feito: PR #1, 136,1 s |
| PRs reais do Mathlib no steady-state, com o cache aquecido no branch base (D-61): trivial, médio, fanout no caminho de sucesso e fanout no caminho fail-closed (L-27; ranking de `tools/layer2/fanout.py`), com tempos por `cache_state` (`tools/layer2/timings.py`) e `project_dirty: false` (D-62) | feito: PRs #5–#8, `warm`, 126–142 s; fail-closed à parte (PR #7) |
| Caminho de timeout (`auditor-failed-infra`, sem bloquear merge) | feito: passo 8, PR #9 |
| p95 por arquivo medido e default do timeout por arquivo reajustado | **não feito**: adiado para a Fase 1 (`docs/roadmap.md`, "Timeout por arquivo medido") |
| GitHub Action integrada e testada em fork | feito: `auditor-tier1`, `auditor-label`, `auditor-report` (passo 9, PR #8) e `auditor-warm-cache` no fork |

**Por que duas camadas.** O ambiente de desenvolvimento tem o toolchain Lean (verificado: `lean`, `lake` e `#print axioms` funcionam), mas não tem acesso ao cache de build do Mathlib, e compilar o Mathlib do zero não cabe nele.

**Ambientes de desenvolvimento usados.** Linux (sandbox, até a Etapa A) e Windows 11 com elan, a partir da Etapa B: `leanprover/lean4:v4.22.0` (commit `ba2cbbf0`) até a instrução 11; **`leanprover/lean4:v4.36.0-rc1`** (commit `c9afcddf`, o toolchain do Mathlib `master` em 2026-10-20) desde a instrução 12. A suíte inteira roda no toolchain fixado.

## Conformance suite: o que cada cenário testa

| Cenário | Categoria | Estado esperado |
|---|---|---|
| `01-sorry-target` | admissão no arquivo-alvo | `Rejeitada` / `Conforme`, `sorryAx_detected` |
| `02-sorry-transitive` | admissão transitiva (A → B → C → D) | `Rejeitada` / `Conforme`; origem rastreada até `d_lemma` |
| `03-axiom-unknown` | axioma **desconhecido** nas premissas | `Validada` / `Não resolvido`, `unknown_axiom` |
| `04-implemented-by` | `@[implemented_by]` sozinho e combinado com avaliação nativa | (a) `Não resolvida`, `implemented_by_candidate`; (b) `Rejeitada`, `implemented_by_reaches_native_eval` |
| `04b-extern` | `@[extern]` user-level sozinho e combinado (O-5); (c) com `Nat.add` do toolchain no mesmo enunciado | (a) `Não resolvida`, `extern_candidate`; (b)/(c) `Rejeitada`, `extern_reaches_native_eval`, só `myF` apontado |
| `06-tcb-boundary` | fronteira de TCB (Q7-a), canário: `Nat.add` (`@[extern]` do toolchain) com e sem `native_decide`; uma sonda por raiz da allow-list de raízes (`uses_init`, `uses_lean`, `uses_std`, `uses_lake`; D-42) | nenhuma regra de `extern`/`implemented_by` dispara; sem `native_decide`: `verified`; com: `unresolved` só por `native_auxiliary_axiom` (Q9-a; na v4.22, `verified`); sondas: `verified` |
| `05-native-decide` | mecanismo **proibido** nas premissas (avaliação nativa sem justificativa) e a gramática da justificativa | `Validada` / `Não conforme`; justificado: `Validada` / `Não resolvido` (`native_auxiliary_axiom`, Q9-a; na v4.22, `verified`); órfã: `Rejeitada` |

Sob a ortogonalidade estrita (Q1-X), `sorryAx` é admissão e afeta só `proof_status`; por isso a categoria "proibido nas premissas" é coberta pelo 05, não pelo 02 (R-1).

## O que a ferramenta faz

Dado um arquivo `.lean`, um ambiente fixado (`lean-toolchain` + `lake-manifest.json`) e uma política (`policy.toml`), emite um relatório JSON (schema v1) com:

- status de compilação (sucesso, falha ou timeout);
- `sorryAx` e outras admissões, incluindo as transitivas;
- axiomas usados por cada declaração, com dependências transitivas;
- violações de política: axioma fora da política, `native_decide` sem justificativa, `@[implemented_by]` suspeito, `set_option` que relaxa checagem;
- TCB enumerada componente a componente, com versões e hashes;
- fingerprint do ambiente, para invalidação futura;
- `correspondence_status: "Não auditada"`.

## Arquitetura

```
arquivo.lean ──► Etapa A (parser léxico, Python) ──► candidatos ─┐
                                                                  │
lean-toolchain + lake-manifest ──► lake build ──► .olean ──►      │
   Etapa B: inspetor (metaprograma Lean) ──► dados brutos ────────┤
                                                                  ▼
policy.toml ─────────────────────────────────► agregador (Python)
                                                   │
                                                   ▼
                                    relatório JSON v1 + selo + exit code
```

Os componentes são separados de propósito: quem **lê** o ambiente não é quem **julga**.

**Etapa A — parser léxico (Python).** Varredura léxica do arquivo-alvo, sem elaboração. Sinaliza `sorry`, `admit`, `axiom`, `native_decide`, `@[implemented_by]`, `set_option` suspeitos, declarações de `macro`/`syntax`/`elab`/`notation` no próprio arquivo, comandos fora da allow-list e caracteres Unicode proibidos. **Nunca emite conclusão positiva.** Seu papel é apontar candidatos e capturar o que não existe no ambiente elaborado: `set_option` e comentários.

**Etapa B — inspetor (metaprograma Lean).** Roda depois de `lake build` no ambiente fixado. Importa os módulos compilados via `Lean.Environment` e, para cada declaração do arquivo-alvo, extrai os axiomas transitivos (mesmo algoritmo de `#print axioms`), as admissões (`sorryAx`), o uso de `Lean.ofReduceBool`/`Lean.ofReduceNat`, os atributos relevantes (`@[implemented_by]`, `@[auditor_justified]`) e os metadados para o fingerprint. Produz dados brutos, sem aplicar política. O inspetor é compilado contra o toolchain do projeto-alvo, porque arquivos `.olean` só são legíveis pela mesma versão do Lean; o binário fica em cache, identificado pelo hash do fonte + toolchain, e roda sob `lake env` no projeto-alvo.

O inspetor calcula os axiomas de duas formas: com `Lean.collectAxioms` (o algoritmo oficial de `#print axioms`) e com um fecho de dependências próprio, que também registra quem referencia cada axioma, as constantes com `@[implemented_by]`/`@[extern]` e se cada uma vem do toolchain (decidido pelo caminho do `.olean`, não pelo nome do módulo). Divergência entre as duas formas, constante referenciada inexistente (o algoritmo oficial a ignora em silêncio) ou dona não resolvida viram anomalias, que o agregador converte em fail-closed.

**Allow-list de comandos de projetos (Q5).** A allow-list empacotada cobre só o core. Para um projeto com comandos próprios (o Mathlib define `lemma`, por exemplo), `auditor-gen-allowlist --project <dir>` gera `<dir>/.auditor/allowlist.json` vinculada ao pino do ambiente (`lean-toolchain` + `lake-manifest.json`). A Etapa A só a usa se o pino bater (senão, `allowlist_stale`, fail-closed). Comando do projeto sem classificação explícita em `<dir>/.auditor/classification.toml` é fail-closed (`unclassified_command`).

**Agregador (Python).** Valida a política, aplica as regras aos dados brutos das Etapas A e B, consolida os três estados ortogonais por declaração, monta a TCB e o fingerprint, valida o relatório contra o JSON Schema v1 e define o exit code.

### Por que Python (e não Rust)

O custo dominante de uma execução é `lake build` (segundos a minutos), não o startup do wrapper (milissegundos). A inspeção semântica precisa ser escrita em Lean de qualquer forma, já que só o próprio Lean lê `Lean.Environment`. O wrapper Python só orquestra, faz varredura léxica e aplica regras declarativas. Rust não traria ganho mensurável e reduziria a velocidade de iteração.

## Estados ortogonais

Cada declaração tem três estados independentes, nunca condensados num veredito único.

| Estado | Valores |
|---|---|
| `proof_status` | `Validada` (kernel aceitou e toda verificação obrigatória passou) · `Rejeitada` (violação concreta de política demonstrada) · `Não resolvida` (evidência insuficiente, timeout ou input fora de cobertura) |
| `premises_status` | `Conforme` · `Não conforme` (dependência proibida detectada) · `Não resolvido` (análise incompleta) |
| `correspondence_status` | `Não auditada` — sempre, na Fase 0 |
| `overall_status` | `verified` · `rejected` · `unresolved`, pela tabela abaixo (Q4: o pior estado vence) |

**`overall_status` (Q4: precedência `rejected` > `unresolved` > `verified`).** É a leitura segura para quem só lê esse campo.

| `proof_status` \ `premises_status` | `Conforme` | `Não conforme` | `Não resolvido` |
|---|---|---|---|
| `Validada` | `verified` | `rejected` | `unresolved` |
| `Rejeitada` | `rejected` | `rejected` | `rejected` |
| `Não resolvida` | `unresolved` | `rejected` | `unresolved` |

Todo estado diferente de `Validada`/`Conforme` carrega uma razão explícita e legível por máquina (ex.: `sorryAx_detected`, `unknown_axiom`, `policy_invalid`, `timeout`).

**`Validada` exige, cumulativamente:** compilação bem-sucedida; inspetor concluído para a declaração; nenhuma admissão; política válida; TCB completa; nenhum gatilho de fail-closed na Etapa A ou B. Se faltar qualquer um, o estado é `Rejeitada` ou `Não resolvida`, nunca `Validada`. Axiomas fora da política afetam só `premises_status`; admissões (`sorryAx`) afetam só `proof_status` (ortogonalidade estrita). O consumidor lê `overall_status` primeiro; os estados individuais continuam completos no relatório.

### O selo

O selo é uma string derivada do relatório e sempre declara o que não foi verificado:

```
auditor Tier1 v<versão> · Prova: Validada · Premissas: Conforme ·
Correspondência: Não Auditada · Não coberto: correspondência, kernel,
análise semântica, contextos construtivos · fingerprint: <hash>
```

## Exit codes

| Código | Significado |
|---|---|
| `0` | Todos os checks obrigatórios passaram em todas as declarações (`Validada` + `Conforme`) |
| `1` | Pelo menos uma declaração não está `Validada` + `Conforme`; inclui alvo que **não compila** (Q6) |
| `2` | Falha de infraestrutura: a ferramenta não conseguiu rodar (política ausente ou inválida, ambiente não fixado ou inconsistente, timeout, falha do inspetor); ou arquivo **sem declarações** (`no_declarations_found`, D-15): não há nada a rejeitar, e o usuário precisa ser explícito (`--allow-empty` para arquivos só de imports) |

Input não reconhecido **nunca** resulta em exit `0`.

**Alvo que não compila (Q6)**, incluindo ciclo de imports: exit `1`, `proof_status: Não resolvida`, `overall_status: unresolved`, razão `compile_failure`. É falha do alvo detectada pela ferramenta: não é infraestrutura (exit 2 é para a ferramenta incapaz de rodar) nem violação de política (`Rejeitada`).

## Política (`policy.toml`)

A política é código testado: cada regra tem teste de regressão próprio, e mudança de regra exige auditoria por alguém que não é o autor da regra.

**Política ausente, malformada ou com regra inexistente:** o auditor não aplica default silenciosamente. Todas as declarações saem `Não resolvida` / `Não resolvido` com razão `policy_invalid`, exit `2`.

**Axiomas.**
- Permitidos por padrão: `Classical.choice`, `propext`, `Quot.sound`.
- Proibidos por padrão: `sorryAx`; `Lean.ofReduceBool` e `Lean.ofReduceNat` sem justificativa.
- Axioma auxiliar de avaliação nativa (v4.36+): No `leanprover/lean4:v4.36.0-rc1`, `native_decide` não produz mais `Lean.ofReduceBool`: ele adiciona, por uso, um axioma auxiliar `<dona>._native.native_decide.ax_N : e = true` (`Lean.Meta.nativeEqTrue`), que o kernel não reconfere. O inspetor o reconhece pela forma (`native_auxiliary`); a política o trata como avaliação nativa para as regras de justificativa e do padrão combinado, e **além disso** deixa as premissas `Não resolvido` (`native_auxiliary_axiom`), porque a forma não prova a origem. Decisão da Q9 (opção a): permanente na Fase 0.
- Axioma fora das duas listas: governado por `unknown_axiom_action`, default `fail_closed` (estado `Não resolvido`, razão `unknown_axiom`, com sugestão de atualização da política). O valor alternativo `allow_with_warning` exige justificativa escrita na própria política e teste de regressão.

**`native_decide`.** Bloqueado por padrão. Permitido somente com justificativa na docstring da declaração dona, numa única linha com gramática estrita:

```lean
/-- Texto livre da docstring.
auditor_justified: reason="motivo" reviewer="@handle" -/
theorem t : 10 < 20 := by native_decide
```

A Etapa B lê a docstring do ambiente elaborado (`.olean`) e associa a justificativa pelo nome da declaração, não pela posição no arquivo. Não há escape, continuação em várias linhas nem duplicata; qualquer desvio é violação (`native_decide_justification_malformed`). Justificativa numa declaração vizinha não cobre quem usa `native_decide`. Declarações que herdam `Lean.ofReduceBool` transitivamente são rastreadas até a declaração dona. Nenhuma dependência no projeto-alvo é necessária. A aprovação é humana e fica fora do escopo. Detalhes e riscos residuais em `docs/limitations.md` (L-4).

**`@[implemented_by]`.**
- Sozinho, não afeta o kernel: `Não resolvida`, razão `implemented_by_candidate`.
- Combinado: se os axiomas transitivos da declaração incluem `Lean.ofReduceBool` ou `Lean.ofReduceNat` **e** o fecho de dependências da declaração contém uma constante com `@[implemented_by]`, o estado é `Rejeitada`, razão `implemented_by_reaches_native_eval`. Uma justificativa de `native_decide` **não** cobre esse caso. O padrão está escrito na política e tem teste de regressão próprio.

**`@[extern]` (O-5).** Mesma categoria de risco que `@[implemented_by]`: substitui a implementação compilada, e `native_decide` confia nela. Regras análogas (sozinho: candidato; combinado com `Lean.ofReduceBool`/`Lean.ofReduceNat`: `Rejeitada`), com cenário próprio (`04b-extern`, ground truth: deriva `False`).

**Fronteira de TCB (Q7, opção a).** As regras de `@[implemented_by]` e `@[extern]` só se aplicam a declarações **user-level**. Implementações do próprio toolchain (`Nat.add`, `Lean.Name.str`, …) são TCB e não disparam nada. A fronteira é declarada pelo toolchain (raízes de biblioteca em `<sysroot>/lib/lean`) e pelo `lake-manifest.json` (pacotes do usuário), nunca pelo nome do módulo. O que não puder ser decidido é `Não resolvida` (`tcb_boundary_unresolved`). Algoritmo e manutenção em `docs/tcb.md`; o canário é o cenário `06-tcb-boundary`.

**`set_option`.** Allow-list versionada. `maxHeartbeats 0` é **sempre** violação na política default, em qualquer caminho. Uma política customizada pode isentar, mas só com duas condições cumulativas: (a) o arquivo está numa allow-list explícita de caminhos; e (b) a opção está na forma `set_option maxHeartbeats 0 in` aplicada a uma declaração cuja docstring tem `auditor_justified: reason="test-only heartbeat exemption" reviewer="@handle"`. `set_option maxHeartbeats 0` em nível de arquivo ou seção nunca é isentável.

**Escopo da violação de `maxHeartbeats 0`:** invalida **apenas a declaração que o usa** (forma `in`). As demais declarações do arquivo são avaliadas normalmente e passam se não dependerem dela. Uma declaração que **depende** da violadora mantém o próprio estado (pode ser `Validada` + `Conforme`); a dependência fica visível no campo `depends_on_rejected`. Em nível de arquivo ou seção, a opção atinge todas as declarações sob seu alcance, e cada uma é marcada individualmente. `autoImplicit true` e `checkBinderAnnotations false` são violações por padrão.

## Unicode

Allow-list versionada, alinhada a Unicode TR36/TR39.

- **Controles bidirecionais e caracteres de largura zero**, em qualquer posição (inclusive comentários e strings): fail-closed. É risco de segurança real (Trojan Source).
- **Confusables** (por exemplo, letras cirílicas que imitam latinas): warning no relatório, sem falha. O kernel não se confunde; o risco é para o revisor humano.
- Unicode matemático usual (`ℝ`, `∀`, `∑`, …) é permitido.

## Fingerprint do ambiente

Hash que captura:

- versão exata do `lean-toolchain`;
- commit do Mathlib e hash do `lake-manifest.json`;
- hash do inspetor (fonte e binário compilado);
- versão e hash da fonte do agregador, e versão do interpretador Python;
- versão do parser da Etapa A e da allow-list;
- versão e hash da política;
- hash dos metadados importados transitivamente: todos os `@[simp]`, `@[ext]`, `@[reducible]` e `@[implemented_by]`.

Mudança em qualquer componente invalida os selos emitidos contra o fingerprint anterior. A Fase 0 não faz isso automaticamente: o relatório declara o fingerprint, e o consumidor compara com o ambiente atual.

## TCB (Trusted Computing Base)

Todo relatório enumera a TCB contra a qual o selo foi emitido. Mínimo:

| Componente | Identificação no relatório |
|---|---|
| Kernel do Lean | versão + commit do toolchain |
| Toolchain (elaborador, `lake`) | `lean-toolchain` exato |
| Mathlib e demais dependências | commit + hash do `lake-manifest.json` |
| Inspetor (metaprograma Lean) | hash |
| Agregador (Python) | versão + hash + versão do interpretador + dependências Python transitivas com versão exata (`jsonschema` e o que ele puxa; D-20) |
| Parser da Etapa A | versão + versão da allow-list |
| Política | versão + hash |

TCB incompleta impede `Validada`. Detalhes em `docs/tcb.md`.

## Uso

```
auditor check <arquivo.lean> --output report.json --policy policy.toml
        [--timeout-file 90] [--timeout-test artificial] [--allowlist <allowlist.json>]
```

Requisitos: Python ≥ 3.11 com `jsonschema` (`pip install -e .`), e `elan` no `PATH` com o toolchain do projeto-alvo. O arquivo precisa estar num projeto Lake com `lean-toolchain` e `lake-manifest.json`. A primeira execução com um toolchain novo compila o inspetor (cerca de 15 s); as seguintes reutilizam o binário em cache.

Para projetos com comandos próprios (Mathlib), gere antes a allow-list do projeto: `auditor-gen-allowlist --project <raiz>` (ver `docs/maintenance.md`).

O relatório é validado contra `schema/report-v1.json` antes de ser gravado. Cada declaração traz `seal`, a string do selo, que sempre declara o que não foi verificado.

O ambiente vem do `lean-toolchain` e do `lake-manifest.json` do projeto que contém o arquivo. Nenhuma versão de Lean, Mathlib ou política é codificada na ferramenta.

## Integração CI

GitHub Action `auditor-tier1` (workflow reutilizável `.github/workflows/auditor-tier1.yml` + modelos em `ci/templates/` para o repositório-alvo; detalhes e instalação no fork em `docs/ci.md`):

- roda em PRs que tocam arquivos `.lean`, acionada pelo workflow do repositório, sob identidade do repositório; o job que compila o código do PR tem só permissão de leitura (o label é aplicado por um workflow separado que nunca executa código do PR);
- publica o sumário no **Job Summary** da execução e anexa o relatório JSON completo como artefato;
- **não comenta no PR automaticamente.** Um comentário com o sumário só é postado quando um humano o pede explicitamente no PR (`@auditor report`);
- **orçamento de 5 minutos de wall-clock do PR**, do trigger ao relatório, incluindo `lake exe cache get` (steady-state). Se não concluir: exit 2, label `auditor-failed-infra`, **não bloqueia o merge** e exige revisão humana explícita. Timeout nunca é tratado como sucesso;
- **timeout por arquivo de 90 s**: um arquivo que o estoura encerra a auditoria do PR (exit 2);
- o relatório declara `cache_state` (`cold`, `delta`, `warm`). Com cache cold (primeiro run), o orçamento é estendido (15 min), o resultado declara `first_run: true`, e passar dos 5 min não é falha: `cache_cold_extension` e label `auditor-first-run`;
- toda action é fixada por SHA de commit.

## Limitações

- **Etapa A não é parsing fiel.** A sintaxe do Lean é extensível: o parser depende de notações importadas. A Etapa A faz varredura léxica e detecta macros e notações declaradas no próprio arquivo; notação vinda de import só é coberta pela Etapa B. A allow-list é versionada por toolchain, e um teste falha se ela ficar defasada em relação ao `lean-toolchain` fixado (ver `docs/maintenance.md`).
- **`set_option` e comentários só existem na Etapa A**, porque não são registrados no ambiente elaborado.
- **Fingerprint não é revogação.** Detectar que um selo ficou obsoleto é responsabilidade do consumidor na Fase 0.
- **`Classical.choice` é permitido por padrão.** Contextos construtivos são assunto da Fase 3+.
- Lista completa em `docs/limitations.md`.

## Princípios

1. **Assimetria de erro.** Falso "verificado" é catastrófico; "não resolvido" para prova correta é só inconveniente.
2. **TCB enumerada por selo.**
3. **Fail-closed.** Input não reconhecido gera falha explícita com razão, nunca selo positivo.
4. **Nenhum LLM no caminho crítico.**
5. **Ground truth independente.** Testes negativos usam contraexemplo verificável ou prova da negação no Lean.
6. **O selo declara o que não foi verificado.**
7. **Expiração vinculada ao fingerprint.**
8. **Nenhum bot autônomo.**

## Documentação

- `docs/tcb.md` — manifesto completo da TCB
- `docs/invalidation.md` — modelo de dados de selos e revogação (implementação na Fase 1)
- `docs/limitations.md` — limitações detalhadas
- `docs/maintenance.md` — manutenção da allow-list, do inspetor, dos testes de mutação e da fixação de versões dos workflows
- `docs/ci.md` — integração CI, segurança dos workflows, instalação no fork e roteiro da evidência da camada 2 (ferramentas em `tools/layer2/`)
- `docs/roadmap.md` — itens já decididos da Fase 1 (que só começa depois da camada 2)
- `docs/layer2-checklist.md` — passo a passo da camada 2 (comandos, verificações, critérios de abortar, formato do relatório), para o mantenedor executar
- `CHANGELOG.md` — mudanças que afetam quem usa o auditor
- `docs/proposed-improvements.md` — objeções registradas à especificação
