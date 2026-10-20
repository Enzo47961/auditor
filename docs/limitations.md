# Limitações (Fase 0, Tier 1)

Referência normativa dos testes: cada limitação tem um identificador `L-n`, citado pelos testes que dela dependem. Uma limitação aqui é algo que a ferramenta **sabidamente não cobre**; nunca é motivo para emitir `Validada`.

## L-1. O kernel e o compilador estão na TCB, não são auditados
O kernel do Lean é âncora de confiança. Com `native_decide`, a confiança se estende ao compilador e a toda implementação alcançada por `@[implemented_by]`. O cenário 04 demonstra o risco: uma implementação mentirosa permite derivar `False` (`tests/conformance/04-implemented-by/GroundTruth.lean`). Por isso o padrão combinado é `Rejeitada`.

## L-2. A Etapa A é varredura léxica, não parsing
A sintaxe do Lean é extensível e o parser depende de notações importadas. A Etapa A:
- **só vê o texto do arquivo-alvo**. Um `sorry` transitivo (cenário 02) e um ciclo de imports são invisíveis para ela; quem cobre isso é a Etapa B;
- **checa comandos só na coluna 0**. Um token na coluna 0 que não esteja na allow-list nem entre os tokens de continuação (`|`, `where`, …) resulta em `unknown_command` (fail-closed). Consequência: uma continuação legítima escrita na coluna 0 gera falso "não reconhecido" (inconveniente, nunca selo falso). Comandos indentados não passam por essa checagem;
- **detecta comandos de risco em qualquer posição** (`macro`, `notation`, `run_cmd`, `#eval`, …). São tokens reservados do Lean e não podem ser identificadores, exceto entre `«»`;
- **não conhece comandos do Mathlib** (`lemma` e outros). Sem uma allow-list do Mathlib, todo arquivo do Mathlib resulta em `unknown_command` (ver Q5 em `proposed-improvements.md`);
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
O caminho `auditor-failed-infra` é testado com limite reduzido e declara `timeout_test: artificial` no relatório. Latência real só vem das medições em PRs do Mathlib (camada 2 do Done).

## L-12. Cobertura do ambiente do builder
Sem acesso ao cache do Mathlib, o ambiente de desenvolvimento só verifica fixtures sem Mathlib. Medições reais e o teste da Action em fork são evidência trazida pelo mantenedor.

## L-13. `@[extern]` não é coberto
Assim como `@[implemented_by]`, `@[extern]` substitui a implementação compilada, e `native_decide` confia nela. A spec cobre só `implemented_by`. Funções do core (aritmética de `Nat`) usam `extern`, então todo `native_decide` confia em código C do runtime. Registrado como observação O-5; não implementado.
