# Invalidação de selos — modelo de dados

**Estado: só modelo.** Na Fase 0 nada deste documento está implementado além do que o relatório já emite: fingerprint e TCB por declaração. Armazenamento de selos, log de eventos, propagação e assinatura são da Fase 1. Este documento fixa o modelo para que a Fase 1 não precise reinterpretar o relatório v1.

## Princípios

1. **Selos são imutáveis.** Um selo nunca é editado nem apagado. A situação atual de um selo é **derivada**: selo + log de eventos + ambiente do consumidor.
2. **Revogação é um evento, não uma edição.** Eventos são acrescentados a um log *append-only*; nenhum evento é removido. Um evento emitido por engano é neutralizado por outro evento (`retraction`), que também fica no log.
3. **Obsoleto não é revogado.** Um selo emitido contra outro ambiente (fingerprint diferente do atual) é **obsoleto**: não se aplica ao ambiente do consumidor, mas também não foi refutado. Um selo **revogado** foi declarado inválido por um evento. As duas situações nunca são confundidas.
4. **Na dúvida, não vale.** Se o consumidor não consegue decidir o estado de um selo (log inacessível, evento malformado, fingerprint ausente), o estado é `indeterminado`, nunca `válido` (fail-closed, princípio 3).
5. **Humano no circuito.** Eventos de revogação são criados por pessoas identificadas (princípio 8). A ferramenta pode **detectar** mudanças de ambiente, mas não emite revogação por conta própria.

## Entidades

### Selo (`Seal`), imutável

Derivado de uma entrada de `declarations` de um relatório v1. Todos os campos já existem no relatório (entre parênteses, o campo de origem).

| Campo | Origem no relatório v1 | Observação |
|---|---|---|
| `seal_id` | — | SHA-256 da forma canônica (JSON, chaves ordenadas) dos campos abaixo, exceto `issued_at` e `report_sha256` |
| `declaration_name` | `declaration_name` | |
| `declaration_hash` | `declaration_hash` | identidade do conteúdo elaborado (D-18) |
| `module` | `target.module` | |
| `proof_status`, `premises_status`, `overall_status` | idem | o selo registra o resultado, inclusive os negativos |
| `correspondence_status` | idem | sempre `Não auditada` na Fase 0 |
| `fingerprint` | `tcb.fingerprint` | ambiente contra o qual o selo vale |
| `tcb` | `tcb` | componentes enumerados (kernel, toolchain, dependências, inspetor, agregador, parser, política, metadados) |
| `depends_on_rejected` | idem | |
| `local_dependencies` | (Fase 1: `depends_on` completo do inspetor) | declarações do mesmo módulo no fecho; dependências de outros módulos são cobertas pelo fingerprint (imports fixados pelo manifest) |
| `issued_at` | `execution_metadata.timestamp` | |
| `report_sha256` | — | hash do relatório de onde o selo foi extraído (rastreabilidade) |

Selo com `fingerprint: null` (TCB incompleta) não é armazenável como selo: o relatório já garante que essa declaração não é `Validada`.

### Evento (`Event`), append-only

| Campo | Tipo | Observação |
|---|---|---|
| `event_id` | SHA-256 da forma canônica do evento sem `event_id` | |
| `kind` | enum, abaixo | |
| `selector` | objeto, abaixo | **quais** selos o evento atinge |
| `reason` | texto | obrigatório |
| `evidence` | lista de referências (URL, commit, issue, relatório) | obrigatório para `revocation` |
| `author` | identidade humana | princípio 8; nunca uma conta de automação |
| `created_at` | timestamp | |
| `supersedes` | `event_id` ou nulo | só para `retraction` |

**Tipos (`kind`):**

| `kind` | Efeito nos selos selecionados | Exemplo |
|---|---|---|
| `revocation` | `revogado` | bug no kernel 4.36.0-rc1; defeito no inspetor v2 que omitia axiomas; política v1 tinha regra errada |
| `retraction` | anula o efeito de um evento anterior (`supersedes`) | revogação emitida para a versão errada |
| `advisory` | nenhum efeito no estado; o aviso aparece para o consumidor | regra de política reconsiderada, sem erro demonstrado |

**Seletor (`selector`):** conjunção de condições sobre campos do selo. Exemplos:
- `{"tcb.kernel.lean_version": "4.36.0-rc1"}`
- `{"tcb.inspector.source_sha256": "sha256:…"}`
- `{"tcb.policy.sha256": "sha256:…", "declaration_name": "foo"}`
- `{"fingerprint": "sha256:…"}`

Um seletor vazio é inválido (não existe revogação de "tudo" por omissão).

## Estado derivado de um selo

Entrada: o selo `S`, o log `L` e o fingerprint do ambiente atual do consumidor `F` (calculado pela mesma função de `src/auditor/fingerprint`).

1. Se `L` não pôde ser lido ou contém evento malformado → `indeterminado`.
2. Remover de `L` os eventos anulados por `retraction` válidas.
3. Se algum `revocation` restante seleciona `S` → `revogado`.
4. Se algum selo **do qual `S` depende** está `revogado` (propagação, abaixo) → `revogado` (causa: `propagated`, com o caminho).
5. Se `S.fingerprint ≠ F` → `obsoleto`.
6. Se `S.overall_status ≠ verified` → `negativo` (o selo registra rejeição ou não resolução; continua imutável e consultável).
7. Senão → `válido`.

A ordem importa: revogação prevalece sobre obsolescência. Um selo revogado continua revogado mesmo quando o ambiente muda.

## Propagação

Revogar um selo pode invalidar outros que dependem dele.

- **Mesmo módulo:** se `S` lista `T` em `local_dependencies` e `T` está revogado, então `S` está revogado (transitivamente, até ponto fixo).
- **Outros módulos:** não há aresta explícita. Uma dependência importada é fixada pelo manifest e pelos commits, que entram no fingerprint. Revogar algo de uma dependência é expresso por seletor sobre os componentes do fingerprint (por exemplo, `tcb.dependencies.mathlib_commit`), e não por arestas entre selos. Isso evita que o modelo dependa de um grafo global de declarações que a Fase 0 não constrói.
- **Componentes da TCB:** revogar um componente (kernel, inspetor, agregador, política) é um seletor sobre `tcb.*`, que atinge diretamente todos os selos emitidos com ele. Não precisa de propagação.
- **Ciclos:** o fecho de dependências do Lean é acíclico para declarações elaboradas; a propagação itera até ponto fixo e termina.

## O que a Fase 0 já garante

- O relatório declara `fingerprint` e a TCB completa em cada declaração; `Validada` exige TCB completa (schema v1).
- `declaration_hash`, `depends_on_rejected` e os estados ortogonais têm os campos necessários para extrair selos sem reinterpretação.
- Comparar o fingerprint com o ambiente atual é responsabilidade do consumidor (L-10).

## Fora do modelo (Fase 1+)

- Assinatura criptográfica de selos e eventos, e identidade verificável do autor.
- Onde o log é guardado e como é distribuído.
- `local_dependencies` completo no relatório (hoje só `depends_on_rejected` é emitido).
- Revogação automática a partir de detecção de mudança de ambiente. Isso não está previsto: a detecção é automática, mas a revogação é humana.
