# Estudo de usuário (Fase 1, sub-fase 1c)

```
status: metodologia aprovada (instrução 27); convite aprovado; seleção dos PRs e defeitos plantados em preparação; recrutamento pendente
classificação: author-self-review (L-26)
```

**Pergunta (instrução 24).** A ferramenta reduz o tempo humano líquido de revisão? Ou seja, T_net = T_convencional − T_assistido > 0, com taxa de falsos alertas abaixo de 30 %.

## 0. Escopo: opção (B) da instrução 26

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
| Taxa de falsos alertas | alertas do auditor (declaração não `verified`) que o revisor e o ground truth (ou a aceitação do PR no Mathlib) julgam infundados / alertas totais, por PR |
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
