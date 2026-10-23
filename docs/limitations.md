# Limitações (Fase 0, Tier 1)

Referência normativa dos testes: cada limitação tem um identificador `L-n`, citado pelos testes que dela dependem. Uma limitação aqui é algo que a ferramenta **sabidamente não cobre**; nunca é motivo para emitir `Validada`.

## L-1. O kernel e o compilador estão na TCB, não são auditados
O kernel do Lean é âncora de confiança. Com `native_decide`, a confiança se estende ao compilador e a toda implementação alcançada por `@[implemented_by]`. O cenário 04 demonstra o risco: uma implementação mentirosa permite derivar `False` (`tests/conformance/04-implemented-by/GroundTruth.lean`). Por isso o padrão combinado é `Rejeitada`.

## L-2. A Etapa A é varredura léxica, não parsing
A sintaxe do Lean é extensível e o parser depende de notações importadas. A Etapa A:
- **só vê o texto do arquivo-alvo**. Um `sorry` transitivo (cenário 02) e um ciclo de imports são invisíveis para ela; quem cobre isso é a Etapa B;
- **checa comandos só na coluna 0**. Um token na coluna 0 que não esteja na allow-list nem entre os tokens de continuação (`|`, `where`, …) resulta em `unknown_command` (fail-closed). Consequência: uma continuação legítima escrita na coluna 0 gera falso "não reconhecido" (inconveniente, nunca selo falso). Comandos indentados não passam por essa checagem;
- **detecta comandos de risco em qualquer posição** (`macro`, `notation`, `run_cmd`, `#eval`, …). São tokens reservados do Lean e não podem ser identificadores, exceto entre `«»`. Comandos de risco cujo token é **símbolo** (`?`, `$`) só são detectados no início de comando (coluna 0): o símbolo aparece em termos (`?_`, `?m`, `f $ x`) e não é reservado (D-56);
- **aceita `module` só como primeiro token do arquivo** (cabeçalho do sistema de módulos da v4.36, antes dos `import`). Em qualquer outra posição, `module` é `unknown_command` (D-57);
- **só conhece comandos de projeto com allow-list de projeto** (Q5). Sem `<projeto>/.auditor/allowlist.json`, comandos do Mathlib (`lemma` e outros) resultam em `unknown_command`. A allow-list do Mathlib é evidência da camada 2, gerada no fork (ver `docs/maintenance.md`) e não bloqueia a camada 1;
- vê `decide +native` e `native := …` só como candidatos. A evidência é a Etapa B (`Lean.ofReduceBool`, ou o axioma auxiliar nativo da v4.36);
- não inspeciona o conteúdo de strings interpoladas (`s!"{…}"`).

A allow-list é versionada por toolchain e testada contra ele (ver `docs/maintenance.md`).

## L-3. `set_option` e comentários só são visíveis na Etapa A
Não são registrados no ambiente elaborado. A isenção de `maxHeartbeats 0` só é reconhecida na forma `set_option maxHeartbeats 0 in <declaração>`.

## L-4. Justificativa de `native_decide` por docstring (O-1, opção B)
- **Gramática estrita.** Exatamente uma linha na docstring da declaração dona, no formato
  `auditor_justified: reason="<texto>" reviewer="@<handle>"`.
  Sem escape (`\` ou `"` dentro de `reason` é proibido), sem continuação em várias linhas, sem duplicata. `<handle>` usa letras, dígitos e hífen. Qualquer desvio resulta em `native_decide_justification_malformed`. A única normalização é remover espaços em branco no fim da linha, porque o Lean armazena a docstring com o espaço que antecede `-/` (verificado na investigação O-1).
- **Atribuição por nome, dependente de convenção interna.** A declaração dona é obtida removendo os componentes internos do nome da constante que referencia o axioma de avaliação nativa diretamente (`Lean.ofReduceBool`/`Lean.ofReduceNat`, ou o auxiliar `…._native.native_decide.ax_N` da v4.36; ex.: `nd_justified._proof_1_3` → `nd_justified`). Essa convenção é detalhe do compilador e pode mudar entre versões do Lean. Se a dona não for resolvida, o resultado é `Não resolvida` com razão `native_decide_owner_unresolved`.
- **Justificativa não é autenticação.** Qualquer autor pode escrever a linha. A aprovação do revisor designado é humana e está fora do escopo.
- **Auxiliares `where`.** Na v4.22, o `native_decide` de um auxiliar `where` (ex.: `outer.aux`) passava por `outer._proof_N`, e a dona era `outer`. Na v4.36.0-rc1, o axioma auxiliar se chama `outer._native.native_decide.ax_1_1` (nome derivado da declaração de topo), mas quem o referencia é o próprio `outer.aux`: a dona passa a ser `outer.aux`, que é onde o `native_decide` está escrito. Comportamento observado no toolchain fixado e travado por teste (`tests/stage_b`, fixture `edges`).
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

Funções do próprio toolchain também usam esses atributos: todo `native_decide` sobre `Nat` passa por `@[extern]` do core (`Nat.add`, `Nat.decLt`, `Nat.ble`), e todo `sorry` puxa `@[implemented_by]` do core (`Lean.Name.str`). Pela Q7 (opção a), essas implementações são TCB e não disparam as regras; só as user-level disparam. A fronteira é declarada pelo toolchain, restrita à allow-list de raízes usadas pelo projeto-alvo (D-42), e pelo `lake-manifest.json` (`docs/tcb.md`). O canário é o cenário `06-tcb-boundary`, com uma declaração por raiz da allow-list.

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
**Emendado pela L-33a (Fase 1):** o critério vale para comando, tática, termo ou atributo. Texto original, para histórico:

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

## L-19. Axioma auxiliar de avaliação nativa reconhecido só pela forma (v4.36, Q9)
No `leanprover/lean4:v4.36.0-rc1`, `native_decide` não produz mais `Lean.ofReduceBool`: ele adiciona, por uso, um axioma auxiliar `<dona>._native.native_decide.ax_N : e = true` (`Lean.Meta.nativeEqTrue`), que o kernel não reconfere. O inspetor o reconhece pela forma (`native_auxiliary`); a política o trata como avaliação nativa para as regras de justificativa e do padrão combinado, e **além disso** deixa as premissas `Não resolvido` (`native_auxiliary_axiom`), porque a forma não prova a origem. Um `axiom` escrito à mão com o mesmo nome e o mesmo tipo é indistinguível no ambiente (demonstrado no fixture `edges`: `uses_spoof`). Uma tática importada (de outro arquivo do PR, ou de uma dependência) também pode adicionar um axioma com essa forma sem que a Etapa A do arquivo-alvo veja nada. Por isso o reconhecimento só serve para dar a razão precisa e aplicar as regras mais estritas (justificativa, padrão combinado); nunca leva a `Validada`/`Conforme`.

**Decisão (Q9, opção a, instrução 13): permanente na Fase 0.** `native_decide` nunca sai `verified` na Fase 0. A v4.36 mostrou que certificá-lo dependeria de detalhes internos do compilador que mudam entre versões, e a Fase 0 é desenhada para ser estável contra bumps de toolchain. A reavaliação pelo kernel é item de pesquisa da Fase 1 (`docs/roadmap.md`). Impacto medido no Mathlib fixado (`e1b2403b`): nenhuma prova da biblioteca `Mathlib` usa avaliação nativa, que o linter do próprio Mathlib proíbe; o uso fica em `MathlibTest`. A tática `inclusion` do Mathlib chama `nativeEqTrue` com `+native`, e o axioma que ela gera (`…._native.inclusion.ax_…`) é tratado do mesmo jeito. A medição por PR está na camada 2 (`tools/layer2/native_usage.py`).

## L-20. Axiomas pré-calculados nos `.olean` não são conferidos
Desde a v4.36, o `#print axioms` que um humano roda usa, para declarações importadas, um resumo de axiomas gravado em cada `.olean` na compilação. O auditor não usa esse resumo (D-39): percorre os corpos. Ele também não o compara com o próprio percurso, porque o estado da extensão é privado ao módulo do Lean. Um resumo divergente (`.olean` adulterado ou velho) não é detectado como divergência; não afeta o resultado do auditor, mas pode fazer o `#print axioms` de um humano discordar do relatório.

## L-21. A Fase 0 é voltada ao Mathlib: `target_trusted_roots` vem do fecho do Mathlib
A Fase 0 é voltada ao Mathlib. `src/auditor/data/target_trusted_roots/<toolchain>.json` é o fecho de imports do Mathlib fixado (`e1b2403b`: `Init`, `Lake`, `Lean`, `Std`). Projetos Lean que não são o Mathlib devem gerar o próprio `target_trusted_roots` com `tools/gen_tcb_roots.py`. Módulos de raízes não usadas pelo alvo são classificados como user-level e disparam as regras de `@[extern]`/`@[implemented_by]`. Esse é o comportamento fail-closed correto, mas pode gerar falsos positivos em alvos que não são o Mathlib (por exemplo, um projeto que usa `LeanIR` legitimamente). A descoberta automática de raízes para alvos arbitrários está no roadmap da Fase 1.

## L-22. `fanout.py` não é testado contra o Mathlib na suíte
A suíte não baixa o Mathlib. Por isso `tools/layer2/fanout.py` (D-38) é testado só com grafos sintéticos (`tests/maintenance/test_layer2_tools.py`), e não contra o Mathlib real. A escolha do arquivo de maior fanout é conferida contra o commit fixado no momento da medição, com `--expect-commit` (checklist da camada 2, passo 6), e a saída registra a procedência (commit, SHA-256 do `lake-manifest.json`, `lean-toolchain`). O mesmo vale para `tools/layer2/native_usage.py` e para o `--check` de `tools/gen_tcb_roots.py` (checklist, passo 3).

## L-23. A camada 1 roda no ambiente do autor; bugs entre ambientes só aparecem na camada 2
Os testes da camada 1 rodam no ambiente do autor. Bugs que só aparecem ao cruzar ambientes (fim de linha CRLF/LF, colisão entre bibliotecas do mesmo build, estado de cache, checkout raso do runner) só aparecem na camada 2. Foi o que aconteceu no primeiro `auditor-prep` (instrução 15): D-52 (a extração importava a biblioteca `Cache` do Mathlib junto com a `Mathlib`), D-53 (hash do `lake-manifest.json` calculado num clone CRLF) e D-54 (`--check` sem caso de fork). Nenhum dos três era detectável na camada 1: os fixtures tinham uma biblioteca só, a suíte rodava só no Windows, e o `--check` nunca tinha visto um fork. **A camada 2 não é opcional para considerar o trabalho pronto: é uma categoria distinta de teste.**

## L-24. `gen_tcb_roots.py --check` aceita um fork de medição (relaxamento da camada 2)
O `--check` aceita um `HEAD` diferente do commit gravado em `target_trusted_roots` (D-54) quando, e só quando: (a) o commit gravado é ancestral do `HEAD`; (b) a árvore de trabalho só difere dele em `.github/` e `.auditor/`; e (c) nenhum arquivo `.lean` mudou, nem dentro desses dois prefixos. O invariante que importa é "nenhum `.lean` muda"; restringir aos dois prefixos é o proxy estrito. `.auditor/` entra porque o passo 3 do checklist commita ali a allow-list e a classificação de comandos (D-59): é só configuração do auditor, que não entra no fecho de imports. O relaxamento existe para a medição no fork (`auditor-base` = `e1b2403b` + workflows e configuração do auditor). Fora desse caso, o check continua estrito: mesmo commit, e os dados (raízes, fecho, pacotes, hash do manifesto) comparados byte a byte. No repositório real, em produção, vale o check estrito. Num checkout raso, o commit gravado precisa estar presente (no CI do fork: `fetch-depth: 20`); se não estiver, a ancestralidade não é provada e o check falha.

## L-25. Classificação dos comandos do Mathlib: fail-closed nos casos ambíguos
A classificação dos 98 comandos do Mathlib (`.auditor/classification.toml` do fork, Mathlib `e1b2403b`) marca como fail-closed todo comando cujo efeito não foi possível determinar com certeza lendo a definição: comandos com IO de rede (`#leansearch`, `#loogle`, `#search`), embrulhos que reescrevem o comando (`#deprecate`, `deprecate`), macros que injetam opções escondidas (`#import_bumps`), o registro de elaborador local de `suppress_compilation` e diagnósticos que exibem provas arbitrárias (`#explode`). A classificação pode ser relaxada na Fase 1 com evidência (leitura revisada da implementação no commit fixado e teste que demonstre a ausência de efeito no ambiente que a Etapa B audita). Até lá, arquivos que usam esses comandos não saem `verified`.

Na segunda revisão, entraram também em fail-closed: `#lint`, que executa linters definidos pelo próprio arquivo (`@[env_linter]`); `unsuppress_compilation`, cuja forma `in cmd` reinstala o elaborador de `suppress_compilation`; e `#string_diagram`, por ser ambíguo. Resultado: 60 `allowed`, 35 `metaprogramming`, 3 `syntax_extension`.

## L-26. Revisão da classificação é auto-revisão na Fase 0
A classificação dos 98 comandos do Mathlib foi elaborada e revisada pelo mesmo autor. A revisão externa foi tentada e descartada por falta de identificação e citações de linha divergentes. Qualquer relatório, PR de medição, ou alegação pública de cobertura deve declarar `classification_review_status: author-self-review`. A Fase 1 deve incluir revisão independente antes de qualquer alegação de cobertura do Mathlib em contexto externo.

Mecânica (instrução 19): o `classification.toml` de projeto exige `reviewed_by` (`author-self-review`, `human-reviewed` ou `independent-ai-reviewed`) e `reviewer_independence` coerente (`none` para auto-revisão, `independent` para as outras), mais `revision_note` opcional; sem isso, o gerador recusa (exit 2). A allow-list gerada guarda a declaração (`classification_review`), e todo relatório a repete em `tcb.classification_review_status` (campo obrigatório do schema 1.1.0, incluído no fingerprint). Sem allow-list de projeto o valor é `core-only`; com allow-list de projeto sem classificação, `no-project-classification`; com allow-list de gerador antigo, sem declaração, `undeclared`. A auto-revisão permite os PRs de medição e alegações internas acompanhadas da declaração; não permite apresentar a cobertura do Mathlib a terceiros (Zulip, artigo, blog) sem qualificá-la como auto-revisada.

## L-27. Medição de fanout: caminho de sucesso e caminho fail-closed são categorias separadas
**L-27.** A medição de fanout no caminho de sucesso usa o arquivo de maior fanout cuja Etapa A não tem item não reconhecido. O critério "sem sintaxe declarada" é insuficiente: arquivos como Basic/Logic/Basic.lean usam simproc_decl, Init.lean usa register_linter_set e run_cmd, e ambos falham em fail-closed por motivo diferente de sintaxe. O critério "Etapa A limpa" é o único que garante o caminho de sucesso, e é reproduzível na Fase 1 (mesmo algoritmo de verificação).

Arquivos que a Etapa A não aceita são medidos no caminho fail-closed, categoria separada. A distinção é da arquitetura, não da ferramenta.

Redação anterior (instrução 20), substituída por esta na instrução 21: "A medição de fanout no caminho de sucesso usa o arquivo de maior fanout entre os que não declaram sintaxe. Arquivos que declaram sintaxe são medidos no caminho fail-closed, categoria separada."

Origem (instrução 20): o arquivo de maior fanout sugerido, `Mathlib/Data/Set/Defs.lean` (posição 20, 8092 dependentes), declara `syntax`, `macro` e `prefix`. Pela L-17, toda declaração do arquivo sai fail-closed, inclusive o lema de sonda. Ele continua medido, como "fanout, caminho fail-closed" (PR #4: `unresolved` 37/37, auditoria 6,5 s).

**Achado na aplicação da redação anterior (motivou a emenda):** "não declarar sintaxe" não basta para o caminho de sucesso. Os dois arquivos indicados também saem fail-closed na Etapa A, por metaprogramação:
- `Mathlib/Basic/Logic/Basic.lean` (posição 24): sem sintaxe, mas com `simproc_decl` nas linhas 42 e 75;
- `Mathlib/Init.lean` (posição 1): `register_linter_set` e `run_cmd`.

Varredura das 60 primeiras posições do ranking com a Etapa A e a allow-list do fork: 19 arquivos sem nenhum item não reconhecido. O primeiro é `Mathlib/Lean/Name.lean` (posição 3, 8153 dependentes); o primeiro fora de `Tactic/`, `Lean/` e `Util/` é `Mathlib/Data/String/Defs.lean` (posição 4, 8147). Ou seja, 41 dos 60 (68 %) saem fail-closed na Etapa A (pauta da Fase 1 em `roadmap.md`).

**Escolha (revisor, instrução 21):** `Mathlib/Data/String/Defs.lean` (posição 4, 8147 dependentes). É o primeiro arquivo limpo fora de `Tactic/`, `Lean/` e `Util/`, o mesmo critério de exclusão do PR médio. `Mathlib/Lean/Name.lean` (posição 3) é meta-ferramenta do Lean: só entra como medida adicional de "maior fanout estrito limpo", nunca em substituição.

## L-28. A busca lexical por avaliação nativa superestima
A busca lexical por `native_decide` superestima: casa texto dentro de metaprogramação. A medição real requer inspeção semântica (Etapa B), que é o que a ferramenta faz. Resultado: 0 usos reais em Mathlib@e1b2403b.

Dados (instrução 20): `tools/layer2/native_usage.py` marcou 2 de 256 505 declarações da biblioteca `Mathlib` (0,0008 %), as duas em `Mathlib/Tactic`, e as duas são falsos positivos conferidos à mão:
- o linter que proíbe `+native` e `native_decide` (`Mathlib/Tactic/Linter/DeprecatedSyntaxLinter.lean`, padrões de sintaxe nas linhas 138 a 145);
- a cópia de um campo de configuração, `native := options.native`, na tática `inclusion` (`Mathlib/Tactic/Inclusion/Core/Elab.lean:348`).

Nos 7 relatórios da camada 2 (primeiro run e PRs de medição), nenhuma declaração tem `native_auxiliary_axiom` entre as razões. A medição valida a Q9 retroativamente: o fail-closed permanente de `native_decide` quase não custa cobertura na biblioteca principal, porque o construto não é usado ali.

## L-29. `@auditor report` de quem não tem acesso: não testado end-to-end
O passo 9 testou o fluxo @auditor report acionado por OWNER. Não testou o caminho de um comentário de quem não tem acesso — a garantia é a condição author_association, travada por teste unitário, não testada end-to-end na camada 2. Requer segunda conta para teste end-to-end; fica como pendência de informação, não bloqueante.

Origem: instrução 23. A condição está em `ci/templates/auditor-report.yml` (`author_association` em OWNER, MEMBER ou COLLABORATOR) e é travada por `test_report_workflow_requires_explicit_human_request`. O teste end-to-end está na pauta da Fase 1 (não bloqueia).

## L-33. Código do usuário executado na elaboração por tática ou termo não era detectado pela Etapa A
**Achado da Fase 1 (P0-2, 2026-10-22).** A L-17 tornava fail-closed só os *comandos* que podem executar código na elaboração, antes da Etapa B.

**Demonstração**, no toolchain fixado (`leanprover/lean4:v4.36.0-rc1`):
- `run_tac do (IO.FS.writeFile "marker" "x" : IO Unit)` (tática) e `by_elab do …` (termo) gravaram um arquivo durante o `lake build` do arquivo;
- a Etapa A não registrava nada;
- o auditor dava `verified`, exit 0.

**Natureza da lacuna:** de integridade, não de cobertura (revisor, instrução 24). O código do PR roda no runner, no mesmo usuário que tem o inspetor em cache e o auditor instalado, e a Etapa B não vê a execução: o ambiente Lean não muda, só o sistema de arquivos.

**Resposta: emenda L-33a, implementada na Etapa A v4 e no inspetor v5.** Inventário com fonte em `docs/l33-inventory.md`.

## L-33a. Emenda da L-17: comando, tática, termo ou atributo
**Critério normativo emendado (instrução 24):** um comando, tática, termo ou atributo é fail-closed se pode executar código do usuário em tempo de elaboração, antes que a Etapa B possa inspecionar o ambiente. A L-17 original cobria só comandos.

**Aplicação** (`docs/l33-inventory.md`):
- **Execução no ponto, léxica:** `run_tac` e `by_elab`, em qualquer posição.
  - Resultado **`Rejeitada`** (`elaboration_executes_code`, em `policy_violations`): a execução é violação concreta, não ambiguidade.
  - Vale para todas as declarações do arquivo, porque a execução aconteceu no build que a Etapa B audita.
- **`unsafe`, léxico:** em qualquer posição, `Não resolvida` (`unsafe_code`). Esconde IO num tipo puro, executado se um termo for avaliado na elaboração (configuração de tática, `include_str`, `eval%`).
- **Por ambiente** (inspetor v5): toda constante do módulo-alvo cujo **tipo** alcança `IO.RealWorld` (elaborador, tática, simproc, handler de atributo, procedimento de `initialize`), ou com `@[extern]`, deixa o arquivo `Não resolvida` (`target_defines_executable_code`).
  - Registrar não prova que executou.
  - Não há lista de nomes de atributo: o tipo decide.
- **Dependência alterada no PR:** o alvo que importa (fecho de imports do inspetor) um arquivo alterado com `run_tac`/`by_elab` (ou ilegível) sai `Não resolvida` (`dependency_executes_code`). O `auditor-ci` passa os arquivos alterados a cada auditoria (`--changed`).
- **`show_panel_widgets`** passou de `allowed` a `metaprogramming` (classificação do core v5): avalia termos do arquivo, como `#widget`. A classificação de risco do core passa a valer sobre uma allow-list de projeto gerada antes.

**Limites declarados:**
- **Lacuna de integridade (instrução 25), não de cobertura: dependência alterada que só registra código** (via atributo, `initialize`, `unsafe`), sem `run_tac`/`by_elab`.
  - Ela mesma sai `Não resolvida` como alvo, mas o alvo que a importa **sai `verified`** embora o código registrado tenha executado durante o build dele (o `initialize` de uma dependência executa quando o alvo é compilado: cenário 10).
  - É o mesmo padrão do `sorry` transitivo. A correção, `dependency_registers_code`, detecta no ambiente do alvo o código registrado por dependência alterada.
  - É **P0 da Fase 2** (`roadmap.md`). A mitigação (b) não a fecha: detecta adulteração, não execução.
- **CLI sem `--changed`:** não cruza dependências (`auditor check` sozinho). O `auditor-ci` sempre passa a lista.
- **Dependências externas do Mathlib** (Batteries, Aesop, Qq, ProofWidgets, Plausible, LeanSearchClient, importGraph) não foram inventariadas. A defesa por ambiente vale para o código do alvo, onde quer que o atributo tenha sido definido.
- **`lakefile.lean` alterado no PR** executa código no `lake build`: fora do alcance da Etapa A.
- Para todos esses casos, e para qualquer mecanismo fora do inventário, a defesa é a **mitigação estrutural (b)**: hash do inspetor e do auditor antes e depois do `lake build`, `toolchain_tampered`. Ela detecta adulteração, não execução: (a) e (b) são defesas diferentes, e as duas são necessárias.
- **(b) implementada** (instrução 25, cenário 11). O que ela **não** cobre:
  - adulteração do toolchain Lean (`~/.elan`), do Python ou de outras dependências do runner;
  - adulteração que se desfaz antes da conferência;
  - leitura ou exfiltração (o hash detecta escrita, não leitura).

## L-30. Taxa de fail-closed da Etapa A no top-60 por fanout (P0-2)
Taxa de fail-closed da Etapa A no top-60 é 65,0% após (a); teto de 53,3% mesmo relaxando tudo; a cobertura do Mathlib fica bloqueada até a Fase 2.
- 39 dos 60 falham: 18 só por sintaxe, 7 só por comando não sintático, 14 pelas duas causas. 32 declaram sintaxe genuína, que a instrução 24 mantém fail-closed.
- Sem relaxar `run_cmd`, o teto é 56,7 %.
- O kill criterion do P0-2 (> 50 % depois de (a) e (b)) está atingido.
- **Medida adicional, que não substitui o gate:** na biblioteca `Mathlib` inteira, a taxa é 14,4 % (1244 de 8651). A causa dominante é `notation` (553 arquivos), uma macro gerada pelo toolchain. Se `notation` gerada pelo toolchain puder ser reconhecida como TCB (a mesma lógica do `ctorIdx` do P0-1), a taxa cai muito. Pergunta para a Fase 2 (`roadmap.md`).
- Remedição oficial com a Etapa A v4 (L-33a), run 39849624202: top-60 inalterado (65,0 %); Mathlib inteiro 14,8 % (`unsafe` léxico em 74 arquivos). A detecção por ambiente da L-33a não está nesses números (`docs/p0-2-fail-closed.md`, seção 8).

## L-34. Atributo gerado na elaboração derruba 7,35 % das declarações do Mathlib (P0-1)
Atributo gerado na elaboração é causa de fail-closed em 7,35% das declarações; a política de TCB para gerado precisa de revisão na Fase 2.

**Medição** (`auditor-measure`, run 39845428621; `docs/p0-1-implemented-by.md`): das 330 852 declarações reportáveis do Mathlib `e1b2403b`, 24 322 (7,351 %) saem `Não resolvida` só porque o fecho alcança um `T.ctorIdx` gerado pelo Lean (`@[implemented_by T.ctorIdx._impl]`, `CtorIdx.lean:139`). Pela Q7, a constante é de usuário, por estar num módulo do Mathlib.
- O Mathlib não escreve nenhum `implemented_by` no fonte.
- As áreas mais atingidas são `CategoryTheory`, `Algebra` e `AlgebraicGeometry`.
- É perda de cobertura, não de integridade: nenhuma dessas declarações sai `verified`.
- O reconhecimento estrutural do `ctorIdx` (corpo `getObjTagNat`, valor `casesOn` dos índices) é item da Fase 2, com teste de equivalência no toolchain fixado.

## L-31. Benchmark de enunciados trocados (sub-fase 1b)
Taxa de detecção de enunciados trocados é 100% (meta: 50%); causas de falha são nenhuma — detecção garantida por construção (enunciado falso com a prova original não compila); falsos positivos nas provas corretas são 28,6% (meta: ≤ 10%).

**Medição:** `docs/benchmark.md`; 5ª execução, run 39879879325, auditor `81457ac`, Mathlib `e1b2403b` oficial; 100 casos válidos.
- **Trapaças que compilam** sobre enunciados falsos (`sorry`, `axiom`, `implemented_by` + `native_decide`, `run_tac`, `sorry` transitivo): 11/11 detectadas, razão certa 11/11, 0 falso negativo.
- **Falsos positivos:** 10 de 35 provas corretas difíceis do Mathlib.
  - **Causas:** `ctorIdx` gerado (L-34) e `set_option` `backward.*` fora da política, aplicadas ao próprio teorema; uma instância anônima fica sem vínculo de propósito.
  - **Antes da Etapa A v5:** 34,3 %.
- **Controles** (enunciados originais com prova simples): 0/24 falsos positivos.
- **Limites da amostra:** os negativos são lemas elementares (ground truth formal por instância concreta); "difícil" é aproximado por comprimento de prova; 35 teoremas de 23 áreas.
