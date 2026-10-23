# Estudo de usuário (Fase 1, sub-fase 1c)

```
status: metodologia aprovada (instrução 27); convite aprovado; seleção dos PRs e defeitos plantados em preparação; recrutamento pendente
classificação: author-self-review (L-26)
```

**Pergunta (instrução 24).** A ferramenta reduz o tempo humano líquido de revisão? Ou seja, T_net = T_convencional − T_assistido > 0, com taxa de falsos alertas abaixo de 30 %.

## 0. Escopo: opção (B) da instrução 26, por declaração (instrução 28)

**Granularidade (instrução 28, Q1 (a)).** A exclusão é **por declaração**, não por PR. Por PR, ela eliminava 9 de 13 PRs (seção 8): `backward.*` aparece em quase todo arquivo, muitas vezes numa declaração entre 80. O PR fica no estudo, e o alerta das causas conhecidas é tratado assim:
- **Causas conhecidas** (instruções 26 e 28):
  - `implemented_by_candidate` de `ctorIdx` gerado (L-34);
  - `set_option_unrecognized`/`set_option_unattributed` de opção `backward.*`;
  - `target_defines_executable_code` de delaborador ou de extensão do `positivity` em arquivo matemático (L-35).
- **Briefing:** avisa das causas conhecidas, mas **não diz "ignore"**. Diz: "estes tipos de alerta têm causa conhecida e estão sendo corrigidos; se você os encontrar, registre o tempo gasto neles separadamente". O revisor é instruído a reportar o tempo, não a ignorar.
- **Taxa de falsos alertas do critério (< 30 %):** medida **só sobre os alertas que não são de causa conhecida**.
- **T_net:**
  - o tempo gasto com alertas de causa conhecida é medido à parte e **excluído do T_net principal**;
  - o relatório traz os dois números: **T_net sem causas conhecidas** (o principal) e **T_net com** (para transparência).
- **Classificação dos alertas:** cada alerta é atribuído a uma causa pelo próprio relatório do auditor (código e detalhe da razão), mecanicamente, antes de os formulários serem lidos.

O texto original da opção (B), a seguir, continua valendo para o objetivo e para o registro do escopo.

### Opção (B), texto de 2026-10-23

**A amostra exclui os casos de `ctorIdx` gerado e de opções `backward.*`.**
- **Por quê:** com a ferramenta atual, 28,6 % das provas corretas difíceis saem `Não resolvida` por essas duas causas conhecidas (L-31, L-34). Ambas são fail-closed e as duas são P0 da Fase 2. Medir agora a configuração completa daria um T_net negativo pelo motivo errado: não porque a ferramenta não ajude, mas por duas causas de falso positivo que já se sabe que vão mudar.
- **O que o resultado mede, portanto:** o valor da ferramenta no escopo que ela cobre, não na configuração de produção.
- **Quando corrige:** a Fase 2, depois de corrigir as duas causas, re-mede com a amostra completa.
- **Este registro faz parte do resultado** e acompanha qualquer citação dele.

## 1. Participantes

- **3 revisores reais do Mathlib**, ou no mínimo 2, com a limitação registrada. A experiência de cada um como revisor do Mathlib é declarada no resultado, sem identificação, salvo consentimento.
- **Recrutamento:** o mantenedor envia o convite (`docs/user-study-invite.md`) depois da revisão do texto pelo revisor do projeto.
- **Participação voluntária;** qualquer um pode desistir a qualquer momento.
- **Tempo estimado:** 2 a 3 horas por revisor (seção 4).

## 2. PRs: 10 reais, no fork de medição

- **Origem:** PRs reais do Mathlib integrados depois de `e1b2403b`, reaplicados no fork (`Enzo47961/mathlib4`, branch `auditor-base`) como PRs de medição. O `auditor-tier1` audita cada um.
- **Seleção mecânica**, com os critérios publicados antes da escolha:
  - aplica sem conflito sobre `e1b2403b`;
  - altera de 1 a 5 arquivos `.lean`, com até 300 linhas de diff;
  - não toca `Tactic/`, `Lean/` nem `Util/` (conteúdo matemático);
  - a ordem de escolha é a ordem de integração no Mathlib.
- **Estratos (instrução 24):**
  - 5 do **caminho de sucesso** (a Etapa A aceita todos os arquivos alterados);
  - 5 do **caminho fail-closed** (algum arquivo alterado tem item que a Etapa A não reconhece).
- **Exclusão da opção (B), decidida pelo próprio relatório do auditor:** sai do sorteio o PR em que alguma declaração auditada fica `Não resolvida` por `implemented_by_candidate` de `ctorIdx` gerado, ou por `set_option_unrecognized`/`set_option_unattributed` de opção `backward.*`. A lista de PRs excluídos e o motivo de cada um são publicados com o resultado.
- **Defeito plantado (aprovado na instrução 27).** Mede se a ferramenta ajuda o revisor a achar um defeito que ele perderia, e não só se economiza tempo em PRs corretos.
  - **Condição 1: injetado em PR real, nunca construído.** O defeito entra, com alteração pontual, num dos PRs reais selecionados (reaplicado sobre `e1b2403b`). O resto do PR fica intacto, e o revisor não pode distinguir o PR por inspeção.
    - **PR A (estrato sucesso):** um `sorry` numa dependência a 3 imports de distância do arquivo principal do PR. A alteração na dependência faz parte do diff, como em qualquer PR que toca mais de um arquivo.
    - **PR B (estrato fail-closed):** um `@[implemented_by]` mentiroso com `native_decide` numa declaração do PR.
    - **Ground truth formal:** prova da negação do que o defeito "prova", ou o `sorry` em si (`sorryAx` no fecho), conferida como no benchmark (`docs/benchmark.md`).
  - **Condição 2: três desfechos, reportados separadamente, nunca agregados.** Para cada defeito plantado:
    - **(a)** a ferramenta sinalizou (`Não resolvida`/`Rejeitada`), e o revisor investigou e achou o defeito. Mede o valor da ferramenta;
    - **(b)** a ferramenta sinalizou, e o revisor ignorou o alerta e aprovou. Mede o ruído do alerta;
    - **(c)** a ferramenta não sinalizou. Não deveria acontecer, porque o defeito é fail-closed por construção; se acontecer, é **achado crítico** e entra na L-32.
  - **Aviso aos participantes:** o convite diz que alguns PRs podem conter defeitos plantados, sem dizer quais.
  - **Se os 3 revisores vetarem o plantio:** o parágrafo sai do convite, os 10 PRs ficam todos reais, e esta limitação é registrada: "o estudo não mediu a capacidade do revisor de encontrar defeitos plantados, porque os revisores optaram por não participar dessa parte". O estudo continua; a Fase 2 pode re-medir com plantio, se houver revisores dispostos.

## 3. Desenho: cruzado, com ordem aleatória

- Cada PR é revisado por **2 revisores diferentes**: um **com** o auditor (sumário e relatório do PR) e outro **sem** (só o diff).
- Ninguém revisa o mesmo PR duas vezes. São 20 revisões ao todo, cerca de 7 por revisor, metade com o auditor e metade sem.
- **Conflito de interesse (instrução 27):** um revisor não é atribuído a revisar o próprio PR. Se um dos 10 PRs tiver um dos revisores como autor, esse revisor não é atribuído a esse PR, e a amostra efetiva para esse revisor é 9, não 10. O sorteio aplica essa restrição antes de distribuir, e a autoria de cada PR é publicada com a atribuição.
- **A atribuição e a ordem são sorteadas** com uma semente publicada antes do início, para controlar o efeito de aprendizado e a dificuldade do PR.
- **Condição "sem auditor":** o revisor recebe o diff do PR (link do commit, sem a página do PR no fork, que mostra o sumário).
- **Condição "com auditor":** o revisor recebe a página do PR no fork, com o Job Summary e o relatório.
- **O que cada revisão pede:** decidir se o PR pode ser integrado do ponto de vista da integridade das provas (`sorry`, axiomas, avaliação nativa, código que roda na elaboração, comandos de risco). Correspondência e estilo ficam fora, como no auditor.

## 4. Medidas

Cada revisor registra num formulário, por revisão:
- início e fim da revisão;
- veredito (íntegro / não íntegro / não sei) e os problemas achados;
- **na condição com auditor:** o tempo gasto lendo o relatório, e se algum alerta pareceu falso (com o motivo).

**Derivadas, sempre por PR e por estrato, nunca só agregadas:**

| Medida | Definição |
|---|---|
| T_convencional, T_assistido | tempo da revisão sem e com o auditor, para o mesmo PR |
| **T_net** | T_convencional − T_assistido, por PR; resultado = **mediana** dos 10 PRs |
| Taxa de falsos alertas | alertas **que não são de causa conhecida** (seção 0) que o revisor e o ground truth (ou a aceitação do PR no Mathlib) julgam infundados / alertas que não são de causa conhecida, por PR |
| Alertas de causa conhecida | contagem e tempo, por causa (`ctorIdx`, `backward.*`, delaborador/`positivity`), reportados à parte |
| T_net principal × T_net com causas conhecidas | o principal exclui o tempo gasto com alertas de causa conhecida; o segundo inclui, para transparência |
| Tempo de interpretação | parte do T_assistido gasta lendo o relatório |
| Falso negativo percebido | problema de integridade achado pelo revisor e não sinalizado pelo auditor |
| Defeito plantado | desfechos (a), (b) e (c) da seção 2, por defeito e por condição (com/sem auditor), separados |

O custo por revisor é de cerca de 7 revisões de 15 a 25 minutos, mais 15 minutos de instrução: **2 a 3 horas**.

## 5. Critérios (instrução 24)

- **Aceitação:** T_net > 0 na mediana, com taxa de falsos alertas < 30 %.
- **Se não:** registrar como **L-32**: "T_net é X s (meta: > 0); taxa de falsos alertas é Y% (meta: < 30%)".
- **Kill criterion:** T_net < 0 e falsos alertas > 50 %. Nesse caso a ferramenta aumenta o trabalho humano, e a Fase 2 fica bloqueada até um estudo de acompanhamento mostrar T_net > 0.
- **A Fase 1 não falha por T_net ≤ 0;** falha por não medir ou por medir com amostra enviesada. A exclusão da opção (B) é declarada justamente para não ser um viés escondido.

## 6. Limitações (declaradas antes dos números)

- **Tamanho:** 3 revisores e 10 PRs dão um sinal preliminar, não uma conclusão estatística sobre o Mathlib inteiro. Não haverá teste de significância.
- **Escopo:** a exclusão da opção (B) torna o resultado não representativo da configuração de produção (seção 0).
- **Tempo:** autodeclarado.
- **Recrutamento:** os revisores são voluntários recrutados pelo mantenedor (viés de seleção). A classificação usada pela ferramenta é auto-revisada (L-26).
- **PRs reaplicados sobre `e1b2403b`,** não os PRs originais no momento da revisão real.
- **Defeitos plantados** (se aprovados) são artificiais por definição.

## 7. Dados e publicação

- **Dados brutos:** formulários anonimizados (revisor A, B, C), tempos, vereditos e alertas, publicados com o resultado.
- **Nomes:** só com consentimento explícito de cada participante.
- **Qualificação obrigatória em todo lugar:** a classificação é auto-revisada (L-26), e o escopo é o da opção (B).
- **Resultado:** registrado nesta página e, se for o caso, como L-32.

## 8. Resultado da seleção e da exclusão (B): parada para decisão (2026-10-23)

**Seleção mecânica** (`tools/phase1/study_select.py`; `study/selection.json`): dos 31 PRs integrados ao Mathlib depois de `e1b2403b`, **13 elegíveis**, 8 do estrato sucesso e 5 do fail-closed. Os demais saíram por CI, documentação, infraestrutura, mais de 5 arquivos ou diff que não aplica.

**Exclusão (B), por PR** (`tools/phase1/study_audit.py`; `study/audit.json`; run 39936018705): **9 dos 13 excluídos**.

| PR | Estrato | Exclusão | `verified` / declarações |
|---|---|---|---|
| #45105 | fail-closed | `backward.*` | 0/248 |
| #45097 | fail-closed | mantido | 229/432 |
| #45102 | sucesso | `backward.*` | 82/83 |
| #43841 | sucesso | mantido | 0/88 (só `target_defines_executable_code`: um delaborador) |
| #44400 | sucesso | mantido | 62/62 |
| #44425 | fail-closed | `backward.*`, `ctorIdx` | 0/175 |
| #44511 | fail-closed | `backward.*` | 222/636 |
| #44969 | fail-closed | `backward.*` | 90/293 |
| #45117 | sucesso | `backward.*` | 76/77 |
| #44973 | sucesso | `backward.*` | 88/117 |
| #45025 | sucesso | mantido | 114/114 |
| #45180 | sucesso | `backward.*` | 73/74 |
| #45114 | sucesso | `backward.*` | 177/178 |

**Mantidos:** 3 do sucesso (#43841, #44400, #45025) e 1 do fail-closed (#45097). Faltam 6 para os 10.

**Achado 1: `backward.*` está em quase todo arquivo alterado.** Em 5 dos 9 excluídos, a causa é **uma** declaração entre 74 e 178. A exclusão por PR elimina o PR inteiro por uma declaração.

**Achado 2: a regra por ambiente da L-33a dispara em arquivos matemáticos.** As constantes marcadas (`target_defines_executable_code`) são:
- **delaboradores:** escritos à mão (`@[delab …]`, como `WithAbs.delabToAbs`) ou gerados por `notation`/`notation3` (`…_delab_app_…`);
- **extensões do `positivity`** (`@[positivity]`): `evalIntervalLength`, `evalGelfandRadius`.

Os dois são código que o elaborador executa: delaboradores, ao formatar mensagens durante a elaboração; `positivity`, quando a tática é usada. Pela L-33a, `Não resolvida` é o resultado correto (fail-closed). Mas é um **custo de cobertura não medido até aqui**: no #43841, um único delaborador derruba as 88 declarações do arquivo. Esse custo apareceu em 5 dos 13 PRs. Nos arquivos com `notation`, ele se soma ao fail-closed da Etapa A.

**Decisão pedida ao revisor** antes de o convite ser enviado e de os defeitos serem injetados: relatório de 23/10, perguntas 1 e 2.

**Decisão (instrução 28):**
- **Q1:** opção (a), exclusão por declaração, com a especificação da seção 0. Os 13 PRs elegíveis ficam no estudo.
- **Q2:**
  - L-35, com o alcance medido no Mathlib inteiro;
  - delaboradores e `positivity` como causa conhecida na 1c;
  - a Fase 2 distingue o delaborador escrito à mão (fail-closed correto) do gerado pelo toolchain (candidato a TCB).
- **Defeitos plantados:** em declarações cujo alerta **não** seja de causa conhecida, verificado com o auditor:
  - PR A num PR do estrato sucesso (#44400 ou #45025);
  - PR B no #45097, ou também num do sucesso se o #45097 não tiver declaração elegível.

**Defeitos injetados e conferidos** (`study/defects.json`, `study/defects/`; `auditor-study`, modo `defects`, run 39973055204, auditor `dce313c`):

| Defeito | PR (estrato) | Alteração | Ground truth | Resultado do auditor |
|---|---|---|---|---|
| A | #45025 (sucesso) | `sorry` na prova de `isUnit_mul_self_iff` (`Algebra/Group/Commute/Units.lean`), a 3 imports do arquivo do PR. O lema novo do PR, `Units.isSquare_coe_iff`, o usa. | `sorryAx` no fecho | as duas declarações saem `Rejeitada`, com `sorryAx_detected` |
| B | #45097 (fail-closed) | `@[implemented_by iInterIndexImpl]` (soma) numa auxiliar `private` que calcula `a * b`, mais `native_decide` provando `iInterIndexAux 2 3 = 5` dentro de `measure_iInter_eq_iInf_measure_iInter_le`. O arquivo sai 19/19 verified sem o defeito. | `2 * 3 = 6 ≠ 5`; só o código compilado diz 5 | `Rejeitada`, com `implemented_by_reaches_native_eval` |

Nenhuma das duas razões é de causa conhecida.

**Briefing: onde está o defeito** (instrução 29). O briefing diz explicitamente que um defeito plantado **não está necessariamente na declaração que o revisor está olhando**: pode estar numa dependência. Este é o caso do defeito A, cujo `sorry` está a 3 imports do arquivo do PR. Quando o alerta aponta para uma origem em outro arquivo (as `origins` do `sorryAx_detected`), o revisor deve seguir até lá. O convite não traz essa nuance; ela é do briefing.

**Primeira tentativa do B: erro meu.** Usei `Nat.add` como alvo de `implemented_by`, e o Lean o rejeita. Sem a troca, o `native_decide` avaliou o valor verdadeiro e recusou a proposição (run 39971602437). Corrigi com uma implementação própria, na forma do caso C08 do benchmark.

## 9. Coleta dos dados (instrução 29, item 5)

Preparada antes das respostas dos revisores, para a 1c começar sem atraso. Ferramenta: `tools/phase1/study_run.py`, com testes em `tests/maintenance/test_phase1_tools.py`.

**1. Os 10 PRs** (`study/prs.json`, `study_run.py prs`). A regra mecânica da seção 2 escolhe 5 PRs por estrato, na ordem de integração no Mathlib, entre os 13 elegíveis:
- **sucesso:** #45102, #43841, #44400, #45117, #44973;
- **fail-closed:** #45105, #45097, #44425, #44511, #44969.

Por essa regra, o #45025 é o 6º do estrato sucesso e fica de fora. Por isso o **defeito A foi movido para o #44400**, a outra opção que a instrução 28 autorizou. O novo defeito é um `sorry` em `Set.mul_mem_mul` (`Algebra/Group/Pointwise/Set/Basic.lean`), a 3 imports de `RingTheory/MvPowerSeries/Restricted.lean`. Pelo `to_additive`, o `sorry` chega a `Set.add_mem_add` e daí a `tendsto_sup'_antidiagonal_cofinite`. Dela dependem `MvPowerSeries.tendsto_antidiagonal`, `IsRestricted.mul`, `IsRestricted.subring` e as instâncias que o PR altera. A versão no #45025 está registrada em `study/defects.json` (`history`).

**2. Semente publicada:** `1818766798` (`study/seed.txt`). Foi gerada e publicada em 23/10/2026, antes de qualquer resposta ao convite. O sorteio depende só da semente, de `study/prs.json` e da lista de revisores, então qualquer um pode reproduzi-lo.

**3. Sorteio** (`study_run.py assign`). Cada PR vai para 2 revisores diferentes, um **com** e outro **sem** o auditor. As restrições:
- ninguém revisa PR de que é autor (conflito de interesse, instrução 27);
- a carga é equilibrada (7, 7, 6 com 3 revisores);
- em cada revisor, a diferença entre revisões com e sem o auditor é de no máximo 1;
- a ordem das revisões de cada revisor é aleatória.

O sorteio é por rejeição: vale a primeira tentativa do gerador que satisfaz as restrições, e o número da tentativa é publicado. A identidade dos revisores (`study/reviewers.json`, com o usuário do GitHub para o conflito de interesse) **não** é versionada. A atribuição publicada usa só A, B e C, e lista os pares (PR, revisor) excluídos por conflito.

**4. Formulário** (`study_run.py forms`): um CSV por revisor, com as revisões na ordem sorteada.

| Coluna | Conteúdo |
|---|---|
| `order`, `pr`, `condition` | preenchidas pelo sorteio (`with` = com auditor, `without` = sem) |
| `start`, `end` | início e fim da revisão (ISO 8601, por exemplo `2026-11-03T14:05`) |
| `verdict` | `integro`, `nao_integro` ou `nao_sei` |
| `problems_found` | os problemas de integridade achados, em texto livre |
| `report_reading_min` | só com auditor: minutos lendo o relatório |
| `causes_judged_false` | só com auditor: as **causas** (arquivo:código[:opção], como no relatório) cujo alerta pareceu falso, separadas por `;`, com o motivo em `notes` (instrução 30) |
| `known_cause_min` | só com auditor: minutos gastos com alertas de causa conhecida (seção 0) |
| `noncoverage_min` | só com auditor: minutos gastos com alertas de não-cobertura (`Não resolvida` por fail-closed; instrução 30) |
| `notes` | livre |

**5. Alertas** (`study_audit.py --prs study/prs.json --defects study/defects.json` e depois `study_run.py alerts`). O auditor roda nos 10 PRs **como os revisores os veem**, isto é, com os defeitos plantados aplicados. Cada alerta (declaração não `verified`) é atribuído a uma causa mecanicamente, **antes** de os formulários serem lidos. Um alerta é de causa conhecida quando todas as razões dele são de causa conhecida.

**6. Relatório final** (`study_run.py report`, em `study/result.json`). Traz:
- por PR e por estrato (nunca só o agregado): T_convencional, T_assistido, **T_net principal** (sem o tempo das causas conhecidas), T_net com as causas conhecidas, tempo de leitura e alertas (de causa conhecida e outros);
- a **taxa de falsos alertas**, só sobre os alertas que não são de causa conhecida. O alerta numa declaração com defeito plantado nunca conta como falso;
- a mediana por estrato e no total;
- os **defeitos plantados**: por defeito e por condição, se o revisor achou o defeito, e, na condição com auditor, o desfecho (a), (b) ou (c) da seção 2;
- os critérios da seção 5, escritos no próprio resultado.

**Briefing (15 minutos), conteúdo fixo:**
- o que o auditor verifica e o que não verifica;
- as causas conhecidas e o pedido de registrar o tempo gasto nelas (seção 0, sem dizer "ignore");
- que o defeito plantado pode estar numa dependência, e não na declaração principal (seção 8);
- como preencher o formulário.

## 10. Alertas dos 10 PRs e pergunta antes da primeira revisão (2026-10-23)

O auditor rodou nos 10 PRs como os revisores os veem, com os defeitos aplicados (`auditor-study`, modo `study`, run 39977160187, auditor `ae9f791`). Os defeitos foram conferidos na run 39977153820. Os 10 PRs compilam. Os alertas estão em `study/alerts.json`, atribuídos mecanicamente antes de qualquer formulário.

| PR | Estrato | `verified` | Alertas (declarações): conhecidos / outros | Causas distintas (arquivo + razão): conhecidas / outras |
|---|---|---|---|---|
| #45102 | sucesso | 82/83 | 1 / 0 | 1 / 0 |
| #43841 | sucesso | 0/88 | 88 / 0 | 1 / 0 |
| #44400 (defeito A) | sucesso | 386/441 | 0 / 55 | 0 / 2 (o `sorry`) |
| #45117 | sucesso | 76/77 | 1 / 0 | 1 / 0 |
| #44973 | sucesso | 88/117 | 29 / 0 | 2 / 0 |
| #45105 | fail-closed | 0/248 | 0 / 248 | 2 / 1 |
| #45097 (defeito B) | fail-closed | 227/434 | 0 / 207 | 0 / 5 (2 do defeito) |
| #44425 | fail-closed | 0/175 | 132 / 43 | 3 / 1 |
| #44511 | fail-closed | 222/636 | 2 / 412 | 3 / 3 |
| #44969 | fail-closed | 90/293 | 186 / 17 | 12 / 1 |

Contando por causa distinta, há 25 alertas de causa conhecida e 13 outros. Dos 13, 4 vêm dos defeitos plantados. Os outros 9 são todos `stage_a_unrecognized`: o fail-closed do estrato fail-closed, sem defeito na prova.

**Duas definições a fixar antes da primeira revisão** (relatório de 23/10 ao revisor). Se fossem decididas depois de ver os formulários, isso seria escolher a métrica pelo resultado.
1. **Unidade de alerta: declaração ou causa distinta?** Por declaração, uma única causa num arquivo vira dezenas ou centenas de alertas (88 no #43841, 412 no #44511). Nenhum revisor julga 412 declarações uma a uma, e a taxa ficaria pesada nos arquivos grandes. Por causa distinta (arquivo + código da razão + opção, quando houver), a unidade é o que o revisor de fato lê e julga.
2. **`Não resolvida` por fail-closed conta como falso alerta?** No estrato fail-closed, todo alerta que não é de causa conhecida e não vem de defeito é `stage_a_unrecognized`: a ferramenta diz "não consigo verificar", não "está errado". Se ele contar como falso alerta, a taxa nesse estrato é cerca de 9 em 9, por desenho, e o critério de morte (> 50 %) dispara por construção.

## 11. Pre-registered metrics (instrução 30, 23/10/2026)

**Data do pré-registro:** 23/10/2026. É anterior ao envio do convite, a qualquer resposta e a qualquer formulário. Esta seção substitui as definições de falso alerta das seções 0 e 4 onde elas divergirem. Nada daqui muda depois dos dados; um desvio só pode ser reportado como desvio, com o motivo.

**Artefatos congelados** (commit `4feec56` do auditor; SHA-256 do conteúdo no commit):

| Artefato | Origem | SHA-256 |
|---|---|---|
| `study/alerts.json` | relatórios da run 39977160187 (`auditor-study`, modo `study`), auditor `ae9f791`, Mathlib `e1b2403b` | `9d5b8fe308dc31348db45828de43c229c734185932de17bb213146eb91e42761` |
| `study/categories.json` | `study_run.py classify` sobre os dois de cima | `e4baa167ecba3d8d8dbdf2c7d504dece8ef3eab9bc0157ac2027e091aa984499` |
| `study/defects.json` | ground truth dos defeitos (conferidos na run 39977153820) | `a194581230cd7b7d756d480f333403810a8aae09266bf746643d495d73c2ce03` |
| `study/prs.json` | os 10 PRs (regra mecânica da seção 2) | `59a642a6d264180724b979c8518166206bfbbf1ce84deea0a2d34580d945e3ac` |
| `study/seed.txt` | semente `1818766798`, publicada em 23/10/2026 | `07fafe21461fab9fbfb1d0663936bb56fd9986e4c45de2dba09482abdc689d6d` |
| `tools/phase1/study_run.py` | o código da análise (sorteio, taxonomia, relatório) | `c4d63260fa6898679b0665000deaae33e31bf5aabf2fe57f9be37cd0703073ff` |

### 11.1 Unidade de alerta

**Causa distinta:** arquivo + código da razão + opção, quando houver (por exemplo, `Mathlib/X.lean:set_option_unrecognized:backward.foo`). É a métrica principal, porque é o que o revisor julga. **Declarações afetadas** são sempre reportadas junto, para transparência: sem elas, o leitor não sabe se uma causa afeta 1 declaração ou 412.

### 11.2 Taxonomia (cinco categorias, atribuídas mecanicamente)

| # | Categoria | Declaração | Causa |
|---|---|---|---|
| 1 | Verificação correta | `verified`, sem defeito real | (não há causa) |
| 2 | **Falso alerta** | alguma razão **afirma** problema, sem defeito real | razão afirmativa, sem defeito real |
| 3 | Causa conhecida | todas as razões são de causa conhecida (seção 0) | razão de causa conhecida |
| 4 | Não-cobertura | `Não resolvida`/`Não resolvido` por fail-closed (os demais casos), sem defeito real | razão que não afirma problema |
| 5 | Detecção correta | alguma razão corresponde ao defeito real | razão de `defect_reasons` nos arquivos do defeito |

As regras:
- **Razão afirmativa** é a de efeito `rejected`/`nonconforming` no agregador (`src/auditor/aggregator.py`): `*_detected`, `*_reaches_native_eval`, `elaboration_executes_code`, `orphan_justification`, `set_option_violation`, `forbidden_axiom`, `native_decide_unjustified` e `native_decide_justification_malformed`. As outras dizem "não consigo verificar".
- **Defeito real** é o plantado, pelo `defect_reasons` de `study/defects.json`, ou um defeito achado por revisor e confirmado por ground truth formal. Neste caso, ele é registrado como achado, com a prova, e a declaração passa para a categoria 5.
- **Precedência na declaração:** 1 se `verified`; senão 5, se houver razão de defeito; senão 2, se houver razão afirmativa; senão 3, se todas as razões forem de causa conhecida; senão 4.
- O código é `study_run.classify`, com testes em `tests/maintenance/test_phase1_tools.py`.

### 11.3 Fórmulas

- **Taxa de falsos alertas** (critérios das seções 5 e 6) = categoria 2 / (categoria 1 + categoria 2), em **declarações**, **só no estrato sucesso**.
  - No estrato fail-closed, a categoria 1 é rara, e a taxa não é definida.
  - A categoria 2 também é reportada em causas.
  - A unidade é declaração porque a categoria 1 (`verified`) não tem causa. Esta leitura da fórmula da instrução 30 está marcada para confirmação do revisor.
- **Taxa de não-cobertura** = categoria 4 / todas as declarações, por estrato, com o número de causas e o tempo que o revisor gastou nelas (coluna `noncoverage_min`).
- **T_net principal** = T_convencional − (T_assistido − tempo em causas conhecidas), por PR.
  - O resultado é a **mediana** dos 10 PRs, reportada também por estrato.
  - O tempo em não-cobertura **fica** no T_net: é custo real.
- **T_net secundário** = T_convencional − T_assistido, com as causas conhecidas incluídas, para transparência.
- **Falso alerta percebido:** as causas que o revisor marcou como falsas (`causes_judged_false`), reportadas por categoria e separadas da taxonomia mecânica. Medem a leitura do revisor, não a ferramenta.

### 11.4 Defeitos plantados: os três desfechos

Os desfechos valem para a revisão **com** auditor do PR do defeito:
- **(a)** o auditor marcou o defeito (alguma declaração na categoria 5), e o revisor deu o veredito `nao_integro` e achou o defeito;
- **(b)** o auditor marcou, e o revisor aprovou (`integro` ou `nao_sei`). Mede o ruído do alerta;
- **(c)** o auditor não marcou. É achado crítico e entra na L-32.

Na revisão **sem** auditor, registra-se só se o revisor achou o defeito. Os desfechos são reportados por defeito e por condição, nunca somados.

### 11.5 Critérios (seção 5, com a instrução 30)

- **Aceitação:** mediana do T_net principal > 0 **e** taxa de falsos alertas (estrato sucesso) < 30 %.
- **Kill:** mediana do T_net principal < 0 **e** taxa de falsos alertas > 50 %.
- Os dois critérios são independentes: a não-cobertura pesa no T_net, não na taxa.

### 11.6 O que os dados congelados já fixam (declarado antes dos formulários)

Classificação de `study/alerts.json` (`study/categories.json`), em declarações e (causas):

| PR | Estrato | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| #45102 | sucesso | 82 | 0 | 1 (1) | 0 | 0 |
| #43841 | sucesso | 0 | 0 | 88 (1) | 0 | 0 |
| #44400 | sucesso | 386 | 0 | 0 | 0 | 55 (2) |
| #45117 | sucesso | 76 | 0 | 1 (1) | 0 | 0 |
| #44973 | sucesso | 88 | 0 | 29 (2) | 0 | 0 |
| #45105 | fail-closed | 0 | 0 | 0 (2) | 248 (1) | 0 |
| #45097 | fail-closed | 227 | 0 | 0 | 203 (3) | 4 (4) |
| #44425 | fail-closed | 0 | 0 | 132 (3) | 43 (2) | 0 |
| #44511 | fail-closed | 222 | 0 | 2 (4) | 412 (3) | 0 |
| #44969 | fail-closed | 90 | 0 | 186 (12) | 17 (1) | 0 |

**A categoria 2 é zero em todos os PRs.** Logo, a taxa de falsos alertas do critério já está determinada antes de qualquer revisão: **0 / 632 = 0 % no estrato sucesso**. O que o estudo ainda mede:
- o T_net, principal e secundário;
- a taxa de não-cobertura e o tempo gasto nela;
- os desfechos dos defeitos plantados;
- o falso alerta **percebido** pelos revisores.

Isto é declarado aqui para não parecer, depois, que o critério de precisão foi "aprovado" pelo estudo: ele foi fixado pela saída congelada da ferramenta.
