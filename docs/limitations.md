# Limitações (Fase 0, Tier 1)

Referência normativa dos testes: cada limitação tem um identificador `L-n`, citado pelos testes que dela dependem. Uma limitação aqui é algo que a ferramenta **sabidamente não cobre**; nunca é motivo para emitir `Validada`.

## L-1. O kernel e o compilador estão na TCB, não são auditados
O kernel do Lean é âncora de confiança. Com `native_decide`, a confiança se estende ao compilador e a toda implementação alcançada por `@[implemented_by]`. O cenário 04 demonstra o risco: uma implementação mentirosa permite derivar `False` (`tests/conformance/04-implemented-by/GroundTruth.lean`). Por isso o padrão combinado é `Rejeitada`.

## L-2. A Etapa A é varredura léxica, não parsing
A sintaxe do Lean é extensível e o parser depende de notações importadas. A Etapa A:
- **só vê o texto do arquivo-alvo**. Um `sorry` transitivo (cenário 02) e um ciclo de imports são invisíveis para ela; quem cobre isso é a Etapa B;
- **checa comandos só na coluna 0**. Um token na coluna 0 que não esteja na allow-list nem entre os tokens de continuação (`|`, `where`, …) resulta em `unknown_command` (fail-closed). Consequência: uma continuação legítima escrita na coluna 0 gera falso "não reconhecido" (inconveniente, nunca selo falso). Comandos indentados não passam por essa checagem;
- **detecta comandos de risco em qualquer posição** (`macro`, `notation`, `run_cmd`, `#eval`, …). São tokens reservados do Lean e não podem ser identificadores, exceto entre `«»`;
- **só conhece comandos de projeto com allow-list de projeto** (Q5). Sem `<projeto>/.auditor/allowlist.json`, comandos do Mathlib (`lemma` e outros) resultam em `unknown_command`. A allow-list do Mathlib é evidência da camada 2, gerada no fork (ver `docs/maintenance.md`) e não bloqueia a camada 1;
- vê `decide +native` e `native := …` só como candidatos. A evidência é `Lean.ofReduceBool` na Etapa B;
- não inspeciona o conteúdo de strings interpoladas (`s!"{…}"`).

A allow-list é versionada por toolchain e testada contra ele (ver `docs/maintenance.md`).

## L-3. `set_option` e comentários só são visíveis na Etapa A
Não são registrados no ambiente elaborado. A isenção de `maxHeartbeats 0` só é reconhecida na forma `set_option maxHeartbeats 0 in <declaração>`.

## L-4. Justificativa de `native_decide` por docstring (O-1, opção B)
- **Gramática estrita.** Exatamente uma linha na docstring da declaração dona, no formato
  `auditor_justified: reason="<texto>" reviewer="@<handle>"`.
  Sem escape (`\` ou `"` dentro de `reason` é proibido), sem continuação em várias linhas, sem duplicata. `<handle>` usa letras, dígitos e hífen. Qualquer desvio resulta em `native_decide_justification_malformed`. A única normalização é remover espaços em branco no fim da linha, porque o Lean armazena a docstring com o espaço que antecede `-/` (verificado na investigação O-1).
- **Atribuição por nome, dependente de convenção interna.** A declaração dona é obtida removendo os componentes internos do nome da constante que referencia `Lean.ofReduceBool`/`Lean.ofReduceNat` diretamente (ex.: `nd_justified._proof_1_3` → `nd_justified`). Essa convenção é detalhe do compilador e pode mudar entre versões do Lean. Se a dona não for resolvida, o resultado é `Não resolvida` com razão `native_decide_owner_unresolved`.
- **Justificativa não é autenticação.** Qualquer autor pode escrever a linha. A aprovação do revisor designado é humana e está fora do escopo.
- **Auxiliares `where`.** O `native_decide` escrito num auxiliar `where` (ex.: `outer.aux`) gera `outer._proof_N`, então a dona é a declaração de topo `outer`. Justificativa na docstring de `outer.aux` não é encontrada e resulta em violação (direção segura). Comportamento observado no toolchain fixado e travado por teste (`tests/stage_b`, fixture `edges`).
- **Visibilidade.** A linha aparece na documentação gerada a partir das docstrings.
- **Fallback registrado, não adotado.** Se o Mathlib objetar concretamente à linha estruturada em docstrings, a alternativa é a opção (C): comentário estruturado, arquivo externo `justifications.toml`, ou `native_decide` sempre violação na Fase 0. Não há migração preventiva.

## L-5. `@[implemented_by]` sozinho é só candidato
A ferramenta não verifica equivalência entre a definição e sua implementação. O atributo sem avaliação nativa no caminho do kernel resulta em `Não resolvida` (`implemented_by_candidate`), não em `Rejeitada`.

## L-6. Unicode: confusables são só aviso
Controles bidirecionais e caracteres de largura zero são fail-closed em qualquer posição, inclusive comentários, strings e nomes `«»`. O Lean aceita zero-width dentro de `«»` e o kernel valida a declaração sem axiomas (fixture `tests/fail-closed/namespace-unicode`).

Confusables (TR39 16.0.0) geram warning, nunca falha, em dois casos:
- dois identificadores **do mesmo arquivo** com o mesmo esqueleto e grafias diferentes (ex.: `hi` e `hι`). Componentes de um caractere são ignorados, porque `a`/`α` é convenção matemática;
- um nome `«»` não-ASCII cujo esqueleto é ASCII.

Identificadores importados não entram na comparação. O Lean não aceita Cirílico em identificadores sem `«»` (verificado), então a superfície prática é Grego e nomes entre `«»`.

## L-7. `Classical.choice` é permitido
Contextos construtivos são assunto da Fase 3+. Decisão explícita, não omissão.

## L-8. `maxHeartbeats 0` é higiene, não integridade
Invalida apenas a declaração que o usa. Declarações que dependem dela mantêm o próprio estado; a dependência aparece em `depends_on_rejected`. Veja a objeção O-3.

## L-9. Correspondência não é auditada
`correspondence_status` é sempre `"Não auditada"`. Um teorema que prova a coisa errada pode receber `Validada` + `Conforme`.

## L-10. Fingerprint não é revogação
O relatório declara o fingerprint; comparar com o ambiente atual é responsabilidade do consumidor. Revogação é Fase 1.

## L-11. Teste de timeout é artificial
O caminho `auditor-failed-infra` é testado com limite reduzido e declara `timeout_test: artificial` no relatório. Latência real só vem das medições em PRs do Mathlib (camada 2 do Done). O timeout por arquivo de 90 s e o orçamento estendido de 15 min são valores iniciais, não medidos: o p95 por arquivo da camada 2 decide o default (instrução 11).

## L-12. Cobertura do ambiente do builder
Sem acesso ao cache do Mathlib, o ambiente de desenvolvimento só verifica fixtures sem Mathlib. Medições reais e o teste da Action em fork são evidência trazida pelo mantenedor.

## L-13. `@[extern]` e implementações do toolchain
O-5 aceito: `@[extern]` entra na mesma categoria de `@[implemented_by]`, com cenário próprio (`04b-extern`). O ground truth confirma o risco: um `@[extern "lean_nat_add"]` de usuário sobre uma definição que multiplica deixa `native_decide` provar `myF 2 3 = 5`, e o kernel prova a negação sem axiomas (`False`).

Funções do próprio toolchain também usam esses atributos: todo `native_decide` sobre `Nat` passa por `@[extern]` do core (`Nat.add`, `Nat.decLt`, `Nat.ble`), e todo `sorry` puxa `@[implemented_by]` do core (`Lean.Name.str`). Pela Q7 (opção a), essas implementações são TCB e não disparam as regras; só as user-level disparam. A fronteira é declarada pelo toolchain e pelo `lake-manifest.json` (`docs/tcb.md`), e o canário é o cenário `06-tcb-boundary`.

`partial def` não aparece como `@[implemented_by]` no toolchain fixado (verificado no fixture `edges`).

## L-14. O inspetor está na TCB
O inspetor (`src/auditor/lean/Inspect.lean`) é código confiado: se ele omitir uma declaração ou um axioma, o agregador não tem como saber. Mitigações:
- o fecho de dependências próprio é comparado com `Lean.collectAxioms` (o algoritmo de `#print axioms`); divergência vira `inspector_disagreement` (fail-closed);
- constantes referenciadas e ausentes do ambiente, que o algoritmo oficial ignora em silêncio, viram `missing_constants`;
- os testes da Etapa B comparam os resultados com `#print axioms` rodado pelo próprio Lean, num processo separado;
- hash do fonte e do binário entram na TCB e no fingerprint.

`type_hash` e `value_hash` usam `Expr.hash` do Lean: hash estrutural de 64 bits, determinístico, mas não criptográfico. A composição do `declaration_hash` do relatório será fixada na etapa de Schema.

## L-15. Seleção das declarações reportadas
O relatório cobre as constantes do módulo-alvo que têm faixa de declaração no fonte e nome de usuário (privadas incluídas). Auxiliares gerados (`match_N`, `_proof_N`, recursores, `noConfusion`, equações) ficam de fora, mas aparecem nos fechos de quem os usa. Constantes geradas com faixa no fonte entram: construtor e projeções de `structure`, instâncias anônimas, e o parser criado por `macro` (`tacticObviously`).

## L-16. A allow-list de projeto só é verificada contra o pino
A Fase 0 verifica que a allow-list de projeto corresponde ao ambiente fixado (`env_pin` = `lean-toolchain` + bytes do `lake-manifest.json`), não que a classificação de cada comando é semanticamente correta para o alvo. Correção semântica da allow-list é Fase 1+.

O pino não cobre o código-fonte do próprio projeto. Um comando que o projeto redefina entre a geração e a auditoria mantém a classificação antiga. Um comando novo do projeto cai em `unknown_command` (fail-closed). A sintaxe vinda de import é coberta pela Etapa B (L-2).

## L-17. Critério para comandos `#…` e outros comandos de elaboração (Q8)
**Critério normativo:** um comando é fail-closed na Etapa A se **pode executar código compilado em tempo de elaboração, antes que a Etapa B possa inspecionar o ambiente**. Decisões futuras sobre comandos devem ser derivadas deste critério, não de pesquisa caso a caso.

**Por que este critério.** Um `@[extern]` ou `@[implemented_by]` malicioso em código de usuário pode executar I/O durante a elaboração, antes de qualquer auditoria. Bloquear esses comandos é defesa em profundidade contra **execução pré-auditoria**. A corrupção de axiomas não é o alvo aqui: ela é coberta pela Etapa B, que inspeciona o ambiente elaborado.

Aplicação no toolchain fixado (`classification_version = "3"`):

| Comando | Decisão | Razão |
|---|---|---|
| `#eval`, `#eval!` | fail-closed | executa código compilado |
| `#reduce` | fail-closed | equiparado a `#eval` pelo revisor (D-1) |
| `#guard`, `#widget` | fail-closed | chamam `evalExpr` (verificado no fonte do toolchain) |
| `#guard_expr` | fail-closed | avalia a expressão em tempo de elaboração |
| `#check_tactic`, `#check_tactic_failure` | fail-closed | rodam tática do usuário, que pode chamar `evalExpr`: contornam o bloqueio de `#eval` |
| `#check` | permitido | só checa tipo; não executa nada |
| `#synth` | permitido | síntese de typeclass é unificação; não executa `@[extern]` |
| `#check_simp` | permitido, **revisado** | diagnóstico de `simp`: reduz termos, não executa `@[extern]` compilado |

`#check_tactic_failure` não foi citado na decisão Q8. Foi incluído por derivação direta do critério, porque roda tática do usuário exatamente como `#check_tactic`.

Limite: o critério cobre comandos que **aparecem no arquivo-alvo**. Código executado na elaboração de **dependências** (por exemplo, `initialize` num módulo importado) roda quando o `lake build` compila essas dependências, e isso está fora do alcance da Etapa A do alvo (L-2).

## L-18. Relógio e `cache_state` do CI são medidas do runner
- O relógio do PR começa em `pull_request.updated_at`, o carimbo do evento no GitHub, e é comparado com o relógio do runner; diferença de relógio entre os dois entra na medida. Numa re-execução, o relógio começa no início do job (D-30), e a fila anterior não é contada.
- `cache_state` depende de dois sinais (restauração de `~/.cache/mathlib` e binário do inspetor). Um cache restaurado mas inútil (por exemplo, `.ltar` de outro toolchain) conta como quente; o orçamento estendido nunca é concedido sem sinal frio (D-31).
- Fixação por hash no CI cobre as actions e o elan. O toolchain Lean baixado pelo elan e as dependências Python resolvidas pelo pip não são conferidos por hash no job; suas versões efetivas ficam registradas na TCB do relatório (D-35).
