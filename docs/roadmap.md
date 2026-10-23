# Roadmap

**A Fase 1 não começa antes da camada 2 da Fase 0 estar medida.** O critério de go/no-go da Fase 0 é a camada 2 (GitHub Actions em PRs reais do fork do Mathlib), não a camada 1. Ver o README, seção "Status", e o roteiro em `docs/ci.md`.

## Fase 1 — prioridades P0 (instrução 22)

Antes de qualquer outro item da Fase 1, e antes de qualquer relaxamento de classificação ou de qualquer coisa que se pareça com "aumentar cobertura". Detalhes nas linhas correspondentes da tabela abaixo.

1. **`@[implemented_by]` gerado na elaboração.** O `ctorIdx` do PR #6 é gerado durante a elaboração, não escrito no fonte: a Etapa A não o vê; a Etapa B vê. Medir o alcance no Mathlib: quantos `@[implemented_by]` são gerados e quantos são escritos no fonte. Se for comum, a fronteira de TCB está sendo atravessada por código gerado, o que afeta a política de `implemented_by` (L-5) e a integridade da fronteira de TCB (L-13).
2. **Taxa de fail-closed da Etapa A: 68 % dos 60 arquivos de maior fanout (41 de 60).** Hoje a ferramenta é inútil para a maior parte do núcleo do Mathlib.
   - (a) Reduzir falsos positivos da Etapa A (`match … with`, `do`, `f!"…"` na coluna 0 são o começo; 41/60 indica que a lista real é maior). Medir por categoria antes de relaxar.
   - (b) Relaxar comandos que derrubam o arquivo por motivo não sintático (`simproc_decl`, `register_linter_set`, `run_cmd` etc.), cada um com teste que demonstre ausência de efeito no ambiente que a Etapa B audita.
   - (c) Depois de (a) e (b), medir de novo a taxa de fail-closed nos 60 maiores arquivos. **Se ainda for > 30 %, a ferramenta não está pronta para uso externo.**

**Observação (não prioritária):** no cache `warm`, ~75 % do tempo do PR é preparação (checkout e desempacotamento do cache do Mathlib). A folga de ~160 s no orçamento de 300 s basta para a Fase 0; otimizar fica para quando o orçamento apertar.

A pergunta de pesquisa da Fase 1 (se a hipótese semântica vale a pena) continua em aberto.

## Fase 1 — L-33: defesa contra execução e contra adulteração (instrução 24)

- **(a) Feito (L-33a):**
  - fail-closed léxico de `run_tac`/`by_elab` (Rejeitada) e de `unsafe`;
  - código executável definido no alvo, por ambiente (inspetor v5);
  - dependência alterada com execução (`--changed`);
  - `show_panel_widgets` reclassificado.

  Inventário: `docs/l33-inventory.md`.
- **(b) A fazer, como defesa em profundidade, sem bloquear o (a):**
  - o workflow calcula o SHA-256 do binário do inspetor e do pacote do auditor (`$RUNNER_TEMP/auditor-tool`) no início, roda o `lake build` do alvo e recalcula antes de invocar o inspetor;
  - se mudou, `Não resolvida` com `toolchain_tampered`;
  - **teste:** fixture com `run_tac` que tenta sobrescrever o inspetor deve sair `toolchain_tampered`; o fixture que só grava um marcador não muda o hash, e isso é o esperado.

  (a) defende contra execução, (b) contra adulteração; as duas são necessárias.
- **Pendente da L-33a:**
  - estender o cruzamento de dependências ao código registrado (atributo, `initialize`, `unsafe`) de arquivos alterados;
  - inventariar as dependências externas do Mathlib (Batteries, Aesop, Qq, ProofWidgets, Plausible, LeanSearchClient, importGraph).

## Fase 1 — ordem aprovada (instrução 25)

1. Atualizar o `AUDITOR_SHA` do fork para `a0e3387`, re-aquecer o cache (inspetor v5) e deixar o `auditor-prep` verde. É pré-requisito da 1b.
2. **1b** (benchmark de enunciados trocados) começa depois do item 1. O caminho de sucesso vem do universo de arquivos que a Etapa A aceita na biblioteca inteira (85,2 %), não do top-60 (`docs/benchmark.md`).
3. **Mitigação (b) da L-33** (`toolchain_tampered`) em paralelo com a 1b, como item independente.
   **Implementada (instrução 25):**
   - o inspetor é garantido ANTES do `lake build` do alvo;
   - o hash do binário dele e do pacote do auditor é conferido depois do build; se mudou, o inspetor não roda e o arquivo sai `Não resolvida` (`toolchain_tampered`, exit 1);
   - o `auditor-ci` confere de novo entre um arquivo e outro, porque cada `auditor check` é um processo novo; os arquivos seguintes ficam `not_audited_after_tampering`;
   - cenário de conformidade 11.

Item 1 feito (2026-10-22):
- fork `auditor-base` = `713226a`, workflows no auditor `a0e3387`;
- re-aquecimento com o inspetor v5, run 39858729968;
- `auditor-prep` verde, run 39858970932: allow-list regenerada idêntica byte a byte à commitada, `gen_tcb_roots --check` exit 0, fumaça 20/20.
4. **1c** (estudo de usuário) só depois da (b): o estudo usa PRs reais, e a (b) faz parte da configuração de produção.
   **Opção (B), instrução 26:** a amostra exclui os casos de `ctorIdx` gerado e de `backward.*`. O resultado mede o valor da ferramenta no escopo que ela cobre, não na configuração de produção; a Fase 2 re-mede com a amostra completa (`docs/user-study.md`). O convite vai em `docs/user-study-invite.md`: o mantenedor envia depois da revisão.
5. **1d** só depois da 1c.

## Fase 2 — P0 (instruções 25 e 26)

A Fase 2 começa **depois da 1d**, não antes (instrução 26). Antes de qualquer expansão de cobertura:

1. **`ctorIdx` reconhecido pela forma** (`getObjTagNat` + `casesOn` dos índices), com teste de equivalência no toolchain fixado. 7,35 % das declarações do Mathlib caem só por isso (L-34), em áreas matemáticas (`CategoryTheory`, `Algebra`, `AlgebraicGeometry`). A Fase 2 começa por aí.
2. **`dependency_registers_code`: lacuna de integridade da L-33a.**
   - **O caso:** A está em `--changed` e registra código (`initialize`/`@[init]`, `register_option`, `register_*_attr`, `register_linter_set`, `simproc_decl`, handler de atributo). Então todo B no fecho de compilação do PR que importa A sai `Não resolvida` (`dependency_registers_code`).
   - **Por que é lacuna:** hoje B sai `verified` embora o `initialize` de A tenha executado durante o build de B (cenário 10). É o mesmo padrão do `sorry` transitivo.
   - **A defesa é o inspetor:** no ambiente de B, ele vê as constantes de A e as entradas de extensão que A registrou. A detecção é pelo ambiente, não pelo texto.
   - **Relação com a (b):** a mitigação (b) continua como defesa em profundidade contra adulteração; ela não fecha esta lacuna.
3. **Delaborador gerado pelo toolchain × escrito à mão** (instrução 28). A regra por ambiente da L-33a marca os dois (L-35). A Fase 2 precisa distingui-los:
   - o `@[delab …]` escrito pelo usuário é código de usuário, e o fail-closed está correto;
   - o `…_delab_app_…` gerado por `notation`/`notation3` vem do toolchain, com a mesma lógica do `ctorIdx` e da `notation`.

   Tratar todos como "causa conhecida" relaxaria a política sem teste.
4. **Relaxamento das opções `backward.*`**, com teste de ausência de efeito. É a segunda causa dos falsos positivos da 1b (L-31), junto com o `ctorIdx`. As duas correções devem ser medidas, com a amostra completa do benchmark e do estudo de usuário, antes de qualquer alegação de cobertura do Mathlib a terceiros.

## Fase 2 — pergunta de produto (instrução 25)

- **Política de sintaxe e cobertura de fanout.** O top-60 por fanout é estruturalmente inauditável na configuração atual. 32 dos 60 declaram sintaxe por função, e o teto é 53,3 % de fail-closed relaxando todo o resto (L-30). A Fase 2 não pode prometer cobertura de fanout sem antes mudar a política de sintaxe.
- **A decisão é de produto, não de engenharia:**
  - ou relaxar `notation`/`macro` gerados pelo toolchain (553 arquivos na biblioteca inteira, com a mesma lógica do `ctorIdx`);
  - ou aceitar que o fanout não é coberto.

## Fase 1 — revisão independente da classificação (regras aprovadas, instrução 23)

Origem: a primeira tentativa de revisão independente foi descartada. Era outra IA, sem acesso ao código-fonte, e as citações vieram com linhas deslocadas (`proposed-improvements.md`). Regras, literalmente como aprovadas:

- revisor recebe o fonte no commit fixado, não descrições;
- toda citação traz arquivo, linha e SHA;
- citações conferidas mecanicamente contra o commit antes de aceitar a revisão;
- revisor se identifica e declara grau de independência.

## Fase 1 — fora do fechamento da Fase 0 (não bloqueiam)

- Testar end-to-end um `@auditor report` de quem não tem acesso ao repositório (exige segunda conta; L-29).
- Atualizar retroativamente, com a linha `classificação: … (L-26)`, os comentários do `@auditor report` já postados nos PRs de medição (legado; `proposed-improvements.md`).

## Fase 1 — itens já decididos

| Item | Origem | Decisão |
|---|---|---|
| Hash de declaração resistente a colisão | D-18, instrução 11 | Substituir o hash estrutural de 64 bits (`Expr.hash`) em `declaration_hash` por SHA-256 truncado a 128 bits ou BLAKE3-128, calculado sobre uma serialização canônica do tipo e do valor. 64 bits não resiste a colisão adversarial: quem forja uma colisão troca uma declaração sem mudar o hash. Aceito na Fase 0 só porque ainda não há alvo adversário (L-14). |
| Revogação de selos | `docs/invalidation.md` | Implementar o modelo: selos imutáveis, eventos append-only, estado derivado, propagação. |
| `depends_on` completo | `docs/invalidation.md` | Fecho de dependências locais emitido pelo inspetor, para a propagação de revogação. |
| Timeout por arquivo medido | D-21, instrução 11 | Reajustar o default de 90 s pelo p95 por arquivo medido na camada 2 (`tools/layer2/timings.py`), não por intuição. |
| Reavaliação de `native_decide` via kernel (pesquisa) | Q9 (d), instrução 13 | Item de **pesquisa**, não de entrega: reavaliar o axioma auxiliar `e = true` reduzindo `e` com o kernel, com limite de esforço, sem confiar no compilador. Condições: manter a D-39 (o auditor não executa código do PR) e produzir `verified` em **≥ 50 % dos casos justificados** (medidos num corpus fixado). Se a Fase 1 não atingir o critério, `native_decide` fica **fail-closed para sempre**, e isso é um resultado aceitável, não uma falha do projeto. Para as áreas onde o uso é alto (medido na camada 2, `tools/layer2/native_usage.py`), o relatório declara explicitamente "esta prova usa avaliação nativa; certificação fora de escopo", em vez de um `Não resolvido` sem contexto. **Medição de partida** (Mathlib `e1b2403b`): biblioteca `Mathlib`, 0 provas com avaliação nativa (0 de 256 505 declarações; as 2 detecções léxicas são metaprogramação); `MathlibTest`, 33 de 7 463 (0,44 %), com concentração em `MathlibTest/Algebra` (17 de 34). O corpus para o critério dos 50 % sai de `MathlibTest` e de projetos fora do Mathlib, porque a biblioteca principal não tem casos. A contagem exata, por compilação e por declaração, também é item da Fase 1 (D-51). |
| Descoberta automática de raízes para alvos arbitrários | D-47, L-21, instrução 14 | `target_trusted_roots` hoje é o fecho do Mathlib fixado. Para alvos que não são o Mathlib: descobrir as raízes com o mesmo gerador (`tools/gen_tcb_roots.py`) a partir do projeto-alvo, com a mesma política de verificação: cada dependência conferida contra o `rev` do `lake-manifest.json`, SHA-256 do manifest gravado, drift → fail-closed. Inclui decidir onde fica o arquivo do alvo (no repositório do alvo, como a allow-list de comandos de projeto, ou no auditor) e quem o revisa. |
| Relaxamento da classificação de comandos do Mathlib | L-25, instrução 17 | A classificação do Mathlib (`e1b2403b`) deixou fail-closed, por precaução, os comandos cujo efeito não foi possível determinar com certeza lendo a definição: os 9 ambíguos do rascunho (`#explode`, `#import_bumps`, `#deprecate`, `deprecate`, `#leansearch`, `#loogle`, `#search`, `suppress_compilation`, `#string_diagram`) e, da segunda revisão, `#lint` (executa linters definidos pelo arquivo; relaxável só restringindo-o aos linters do Mathlib fixado) e `unsuppress_compilation` (a forma `in cmd` reinstala o elaborador de `suppress_compilation`; sai junto com ele). `suppress_compilation` é a prioridade: aparece em 41 arquivos da biblioteca. Cada relaxamento exige um teste que demonstre, no commit fixado, a ausência de efeito no ambiente que a Etapa B audita. É agenda de semanas, e é o tipo de trabalho que a Fase 1 deve priorizar: reduz a taxa de `Não resolvida` sem relaxar o fail-closed. |
| Relaxamento das opções `backward.*` | instrução 20 (PR de medição #3) | `backward.isDefEq.respectTransparency`, `backward.isDefEq.respectTransparency.types` e `backward.defeqAttrib.useBackward` aparecem como `set_option … in` no Mathlib real (11 ocorrências só em `Mathlib/Algebra/Homology/Embedding/Connect.lean`). Não estão na política, então as declarações que as usam saem `Não resolvida` (8 de 39 no PR médio; as outras 2 `Não resolvida` do arquivo são `implemented_by_candidate`, linha seguinte). Cada uma precisa de um teste que demonstre, no commit fixado, a ausência de efeito no ambiente que a Etapa B audita, antes de entrar na política. |
| `@[implemented_by]` gerado pelo próprio Lean (**P0**) | instruções 21 e 22 (PR de medição #6) | `CategoryTheory.Limits.WalkingParallelPair.ctorIdx` chega ao fecho de 4 declarações de `Connect.lean` com `@[implemented_by]`, e 2 delas saem `Não resolvida` só por isso (`implemented_by_candidate`, L-5). O fonte do Mathlib não escreve esse atributo (`Equalizers.lean` não contém `implemented_by` nem `ctorIdx`): ele é gerado na elaboração (pelo Lean para o tipo indutivo ou pelo `deriving DecidableEq` da linha 64; mecanismo exato a confirmar), não escrito pelo autor. Pela L-5 o resultado é correto (fail-closed), mas a implementação gerada é do toolchain, não do autor. Fase 1: medir quantas declarações do Mathlib caem só por isso e decidir se implementações geradas pelo compilador para construções do próprio Lean entram na fronteira de TCB, com teste que demonstre a equivalência no toolchain fixado. |
| Taxa de fail-closed da Etapa A no Mathlib real (**P0**) | instruções 21 e 22 (L-27) | **68 % dos 60 arquivos de maior fanout falham na Etapa A** (41 de 60; só 19 saem sem item não reconhecido). (a) Redução de falsos positivos da Etapa A: tokens de continuação na coluna 0 (`match … with`, `do`, `f!"…"`) já foram vistos em `Lean/Meta/Simp.lean`, `MkIffOfInductiveProp.lean` e `SplitIfs.lean`, mas 41/60 sugere que a lista é maior que a registrada; levantar por arquivo o motivo de cada um dos 41. (b) Relaxamento dos comandos que derrubam o arquivo por motivo não sintático (`simproc_decl`, `register_linter_set`, `run_cmd` etc.), com a mesma exigência da linha "Relaxamento da classificação": teste que demonstre a ausência de efeito no ambiente que a Etapa B audita. |
| Toolchain Lean e dependências Python verificados por hash | L-18, D-35, instrução 12 | O CI só confere por hash as actions e o elan. O toolchain Lean (baixado pelo elan a partir de `lean-toolchain`) e as dependências Python (resolvidas pelo pip) passam a ser conferidos também: SHA-256 da release do toolchain fixado contra um valor versionado no repositório, e `pip install --require-hashes` com um arquivo de requisitos com hashes (incluindo o fecho de `jsonschema`). Sem isso, quem compromete o toolchain do Lean ou um pacote PyPI compromete o auditor inteiro — e o auditor é o que detecta comprometimento. |
