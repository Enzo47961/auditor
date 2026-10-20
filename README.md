# auditor — verificador mecânico de integridade de provas Lean 4 (Fase 0, Tier 1)

## O que esta ferramenta NÃO faz

Leia esta seção antes de qualquer outra. Um selo emitido por esta ferramenta **não** significa "a prova está correta" nem "o teorema diz o que o autor afirma".

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

A Fase 0 **não está done**. "Done" tem duas camadas, e a Fase 0 só é considerada done quando as duas estão completas.

**Camada 1 — done no ambiente do builder.** Itens verificáveis sem Mathlib, com evidência produzida no ambiente de desenvolvimento.

| Item | Estado |
|---|---|
| README com limitações e seção "O que NÃO faz" | em revisão |
| Conformance suite (5 cenários) passa | red: todas as asserções decididas; falham por ausência de relatório (CLI não implementada) |
| Fail-closed suite (3 cenários) passa | red fim a fim; a Etapa A já rejeita 2 dos 3 (o ciclo é da Etapa B) |
| Etapa A (pré-scan léxico) | feita: 36 testes, 9 mutações detectadas |
| Schema JSON v1 publicado e validado | pendente |
| `docs/limitations.md`, `docs/maintenance.md` | feito |
| `docs/tcb.md`, `docs/invalidation.md` (só modelo) | pendente |
| Nenhuma dependência de LLM (verificação automatizada) | pendente |
| Nenhuma promessa não cumprida no README | pendente (revisão final) |

**Camada 2 — done no ambiente real.** Exige evidência trazida pelo mantenedor. A Fase 0 não é done sem ela.

| Item | Estado |
|---|---|
| CLI em 3 PRs reais do Mathlib (trivial, médio, núcleo) com tempos medidos, mais o arquivo de maior fanout | **awaiting user evidence** |
| Caminho de timeout (`auditor-failed-infra`, sem bloquear merge) | **awaiting user evidence** |
| GitHub Action integrada e testada em fork | **awaiting user evidence** |

**Por que duas camadas.** O ambiente de desenvolvimento tem o toolchain Lean (verificado: `lean`, `lake` e `#print axioms` funcionam), mas não tem acesso ao cache de build do Mathlib, e compilar o Mathlib do zero não cabe nele.

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

**Etapa B — inspetor (metaprograma Lean).** Roda depois de `lake build` no ambiente fixado. Importa os módulos compilados via `Lean.Environment` e, para cada declaração do arquivo-alvo, extrai os axiomas transitivos (mesmo algoritmo de `#print axioms`), as admissões (`sorryAx`), o uso de `Lean.ofReduceBool`/`Lean.ofReduceNat`, os atributos relevantes (`@[implemented_by]`, `@[auditor_justified]`) e os metadados para o fingerprint. Produz dados brutos, sem aplicar política. O inspetor é compilado contra o toolchain do projeto-alvo, porque arquivos `.olean` só são legíveis pela mesma versão do Lean.

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
| `overall_status` | `verified` só se `Validada` + `Conforme` · `rejected` · `unresolved` (precedência em estados mistos: Q4, pendente) |

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
| `1` | Pelo menos uma declaração não está `Validada` + `Conforme` |
| `2` | Falha de infraestrutura: input inválido, política ausente ou inválida, ambiente inconsistente, timeout |

Input não reconhecido **nunca** resulta em exit `0`.

## Política (`policy.toml`)

A política é código testado: cada regra tem teste de regressão próprio, e mudança de regra exige auditoria por alguém que não é o autor da regra.

**Política ausente, malformada ou com regra inexistente:** o auditor não aplica default silenciosamente. Todas as declarações saem `Não resolvida` / `Não resolvido` com razão `policy_invalid`, exit `2`.

**Axiomas.**
- Permitidos por padrão: `Classical.choice`, `propext`, `Quot.sound`.
- Proibidos por padrão: `sorryAx`; `Lean.ofReduceBool` e `Lean.ofReduceNat` sem justificativa.
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
| Agregador (Python) | versão + hash + versão do interpretador |
| Parser da Etapa A | versão + versão da allow-list |
| Política | versão + hash |

TCB incompleta impede `Validada`. Detalhes em `docs/tcb.md`.

## Uso

```
auditor check <arquivo.lean> --output report.json --policy policy.toml
```

O ambiente vem do `lean-toolchain` e do `lake-manifest.json` do projeto que contém o arquivo. Nenhuma versão de Lean, Mathlib ou política é codificada na ferramenta.

## Integração CI

GitHub Action `auditor-tier1`:

- roda em PRs que tocam arquivos `.lean`, acionada pelo workflow do repositório, sob identidade do repositório;
- publica o sumário no **Job Summary** da execução e anexa o relatório JSON completo como artefato;
- **não comenta no PR automaticamente.** Um comentário com o sumário só é postado quando um humano o pede explicitamente no PR (`@auditor report`);
- se não concluir em menos de 5 minutos: aplica o label `auditor-failed-infra`, **não bloqueia o merge** e exige revisão humana explícita. Timeout nunca é tratado como sucesso.

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
- `docs/maintenance.md` — manutenção da allow-list da Etapa A
- `docs/proposed-improvements.md` — objeções registradas à especificação
