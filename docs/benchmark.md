# Benchmark de enunciados trocados (Fase 1, sub-fase 1b)

```
status: medido (benchmark_version 1); meta de falsos positivos não atingida → L-31
classificação: author-self-review (L-26)
```

Objetivo (instrução 24): mostrar se o auditor encontra os erros que importam, e não só que funciona em provas corretas. As métricas são **por categoria, nunca agregadas**. O benchmark é uma amostra, não prova de cobertura universal.

## 1. População (instrução 25)

- **Caminho de sucesso:** arquivos da biblioteca `Mathlib` (`e1b2403b`) que a Etapa A aceita. São 7369 dos 8651 (85,2 %) na medição oficial com a Etapa A v4 (run 39849624202).
  - Ficam de fora as pastas de infraestrutura: `Tactic/`, `Lean/`, `Util/`, `Mathport/`, `Deprecated/`, `Testing/`. Restam 7184 arquivos.
  - **Não** é o top-60 por fanout: ele é estruturalmente fail-closed (L-30; 32 dos 60 declaram sintaxe por função). A biblioteca inteira é o universo real.

## 2. Categorias

| Categoria | Casos | Construção | Esperado |
|---|---|---|---|
| **Provas corretas difíceis** (`correct_hard`) | 35 | Teoremas do próprio Mathlib, auditados no arquivo original, sem cópia. Seleção determinística (`tools/phase1/benchmark_select.py`, `benchmark/selection.json`), detalhada abaixo | `verified` |
| **Enunciados trocados** (`swapped_statement`) | 24 | Lema real do Mathlib com o enunciado alterado e a prova original, que não se aplica: `<` por `≤`, hipótese removida, `∃` por `∀`, domínio ℕ por ℤ, conclusão mais forte, operação trocada | não `verified` (`compile_failure`) |
| **Controles de validade** (`swap_control`) | 24 | O enunciado **original** de cada troca, com a mesma prova | `verified` |
| **`sorry` e axiomas** (`sorry_axiom`) | 11 | Enunciados **falsos** (os mesmos das trocas) "provados" por trapaça que compila: `sorry` (4), `axiom` próprio (3), `@[implemented_by]` mentiroso + `native_decide` (2), `run_tac` + `sorry` (1) e `sorry` três imports abaixo do alvo (1) | não `verified`, com a razão da trapaça |
| **Inconclusivos** (`inconclusive`) | 6 | Prova **correta** num arquivo com o que a Etapa A ou a política não reconhecem: `macro`, `notation`, `syntax` + `macro_rules`, `unsafe`, `set_option backward.*`, identificador na coluna 0 | `unresolved`, com a razão de fail-closed |

**Seleção das provas corretas:**
- amostra determinística de 800 arquivos (ordem do SHA-256 do caminho);
- `theorem`/`lemma` não privados, com prova de pelo menos 15 linhas;
- no máximo um por arquivo e 4 por área, em rodízio;
- 23 áreas.

## 3. Ground truth independente (instrução 24, princípio 6)

- Todo caso negativo tem **prova formal da negação** (`benchmark/lean/GroundTruth/`), verificada pelo kernel. É sempre uma instância concreta, com `decide`/`norm_num`.
- O próprio ground truth é auditado e precisa sair **`verified`**. Ground truth com `sorry`, axioma ou avaliação nativa invalidaria o caso.
- **Regra de validade.** Um caso negativo só conta se:
  1. o ground truth saiu `verified`;
  2. para enunciado trocado, o controle (enunciado original, mesma prova) também saiu `verified`.

  Sem o controle, um nome de lema errado faria o caso trocado "não compilar" pelo motivo errado. Casos inválidos são listados e excluídos, nunca contados como detecção.
- As trapaças com `implemented_by` + `native_decide` provam uma instância finita do enunciado falso. A falsidade dela é a do ground truth da troca de origem (S03, S14).
- As provas corretas difíceis não têm ground truth próprio: são teoremas do Mathlib, que compila no commit fixado.

## 4. Métricas

Calculadas por `tools/phase1/benchmark.py report`, por categoria:
- **validade:** casos válidos / casos;
- **sensibilidade** (categorias negativas): válidos que não saíram `verified`. **Falso negativo** (negativo válido `verified`) é listado à parte: é o erro catastrófico;
- **razão certa:** o alerta traz um dos códigos esperados (por exemplo, `sorryAx_detected` para `sorry`);
- **taxa de falso positivo** (categorias positivas): provas corretas que não saíram `verified`, com os códigos de cada uma;
- **precisão:** alertas em negativos / alertas totais (negativos + positivos).

**Metas da instrução 24:**
- detectar ≥ 50 % dos enunciados trocados com ground truth formal;
- ≤ 10 % de falsos positivos nas provas corretas.

Se não forem atingidas, o resultado vira a **L-31**, com a taxa real e as causas.

## 5. O que este benchmark mede, e o que não mede (registro honesto antes dos números)

- **Enunciado trocado com a prova original:** a detecção é garantida por construção. Se o enunciado é falso (ground truth formal), nenhuma prova honesta compila, e o arquivo sai `compile_failure`.
  - Esta categoria mede que o auditor **não emite `verified` para arquivo que não compila**. Não mede capacidade de achar o erro.
  - Uma sensibilidade de 100 % aqui é esperada e diz pouco. Abaixo de 100 % seria bug grave.
- **O teste real do auditor é a categoria `sorry_axiom`:** enunciados falsos que **compilam**, porque usam trapaça. Aí se mede se o auditor detecta e classifica a trapaça.
- **Correspondência continua não auditada** (L-9). Um enunciado trocado para algo **verdadeiro** (mais fraco) e provado honestamente sairia `verified`. Isso está fora do escopo e não entra no benchmark, porque a regra de ground truth exige enunciado falso.
- **Viés da amostra:** os casos negativos usam lemas elementares (ℕ, ℤ, ℝ, `Finset`, `List`), porque o ground truth precisa ser formal e conferível. As provas corretas difíceis cobrem as áreas pesadas.
- **Dificuldade:** "difícil" é aproximado por comprimento de prova, não por medida de dificuldade.
- **Falsos positivos nas provas corretas** já são previsíveis em parte, pela L-34 (`ctorIdx` gerado, 7,35 % das declarações) e pela L-33a (código executável no alvo). O benchmark mede quanto disso aparece nesta amostra.

## 6. Execução

- **Onde:** workflow `auditor-benchmark` do fork (dispatch, `auditor-ref`).
- **Passos:**
  1. `lake exe cache get`;
  2. cópia de `benchmark/lean/` para `Mathlib/AuditorBenchmark/`, só no runner (nenhum `.lean` do branch base muda);
  3. `benchmark.py run`: cada arquivo citado pelo manifesto (casos, controles, ground truths), auditado uma vez pelo auditor real;
  4. `benchmark.py report`.
- **Arquivos gerados** por `tools/phase1/benchmark_build.py`, de forma determinística.
- **Conferências:** `tests/maintenance/test_phase1_tools.py` testa o cálculo das métricas (validade, sensibilidade, falso negativo, precisão) e a consistência do manifesto.

## 7. Resultados

### 7.1 Execuções

| Execução | Onde | Auditor | Situação |
|---|---|---|---|
| 1ª (run 39865083826) | fork | `5562afd` | 7 casos inválidos: ground truth ou controle não compilou (imports estreitos; lemas de nome errado); P32 não encontrado (privado pelo sistema de módulos) |
| 2ª (run 39868546708) | fork | `c2d64de`… | com logs de build: confirmou as causas; os enunciados trocados falham por incompatibilidade de tipo (22/24), projeção inválida (S22) e instância (S17, inválido) |
| 3ª (run 39872741098) | fork | `c2d64de` | **100 casos válidos**: medição de referência, Etapa A v4 |
| 4ª (run 39876032952) | fork | `81457ac` | cancelada pelo GitHub (SIGTERM): workflows do fork suspensos por uso intenso |
| 5ª (run 39879879325) | `auditor-measurements` | `81457ac` | **100 casos válidos**: Etapa A v5, Mathlib oficial no commit `e1b2403b` |

Os erros da 1ª e da 2ª execução foram do construtor do benchmark, não do auditor:
- imports estreitos demais no sistema de módulos;
- `native_decide` exige `public meta import` (caso C09);
- casamento do nome privado.

Os casos inválidos foram excluídos, não contados como detecção.

### 7.2 Métricas por categoria

| Categoria | Válidos | 3ª: Etapa A v4 | 5ª: Etapa A v5 |
|---|---|---|---|
| Provas corretas difíceis: falso positivo | 35 | 12 (**34,3 %**) | 10 (**28,6 %**) |
| Controles (enunciado original): falso positivo | 24 | 0 | 0 |
| Enunciados trocados: sensibilidade / falso negativo | 24 | 100 % / 0 | 100 % / 0 |
| Trapaças que compilam: sensibilidade / razão certa / FN | 11 | 100 % / 11 / 0 | 100 % / 11 / 0 |
| Inconclusivos: `Não resolvida` com a razão esperada | 6 | 6 | 6 |
| Precisão dos alertas (negativos / total) | — | 0,745 | 0,778 |

**Entre a 3ª e a 5ª execução, a Etapa A v5 passou a vincular `set_option … in` através de `open … in` e a `instance` com nome.** A política não mudou.
- O achado veio do próprio benchmark: a opção sem vínculo virava efeito do arquivo inteiro e derrubava teoremas que não tinham nada a ver com ela.
- Os dois números ficam registrados.

### 7.3 Falsos positivos restantes (5ª execução)

| Causa | Casos | Pendência |
|---|---|---|
| Só `ctorIdx` gerado (`implemented_by_candidate`, L-34) | P03, P05 | P0 da Fase 2 (reconhecimento estrutural) |
| Só `set_option` fora da política | P12, P14, P26, P29 | opções `backward.isDefEq.respectTransparency`, `…types` e `backward.defeqAttrib.useBackward` aplicadas ao **próprio** teorema; P29 é instância anônima, sem vínculo de propósito. Relaxamento das `backward.*` está no roadmap, com teste de ausência de efeito |
| As duas causas | P02, P08, P25, P28 | as duas acima |

**Leitura:**
- **Nenhum enunciado falso saiu `verified`** em 35 casos negativos válidos. As 11 trapaças que compilam foram detectadas, todas com a razão certa.
- **Os falsos positivos são todos fail-closed**, com causa conhecida e registrada (L-34; política de `set_option`). Nenhum vem de erro de detecção.
- **As provas simples dos controles saem 24/24 `verified`.**
- **O custo de cobertura está nas provas reais do Mathlib,** em áreas pesadas: geometria algébrica, teoria de categorias, topologia algébrica.

### 7.4 Contra as metas da instrução 24

- **Detecção ≥ 50 % dos enunciados trocados:** 100 %, mas **por construção** (seção 5). O número que mede o auditor é o das trapaças: 11/11, com razão certa 11/11.
- **≤ 10 % de falsos positivos nas provas corretas: não atingida, 28,6 %.** Registrado como **L-31**.
- **Kill criterion** (detecção < 20 % e FP > 30 %): não atingido. A detecção é total e o FP fica abaixo de 30 %.
- **Critério de avanço** (detecção ≥ 50 % com FP ≤ 10 %): também não atingido, por causa do FP.

### 7.5 Registro do fechamento (instrução 26)

**1b fechada com a L-31 registrada.** Os três pontos do registro:
1. **O número que mede o auditor é 11/11 nas trapaças que compilam**, com a razão certa e zero falso negativo. Os 100 % de detecção dos enunciados trocados são **por construção**: enunciado falso não compila.
2. **Os 28,6 % de falso positivo se decompõem assim:** 2 por `ctorIdx` (L-34, P0 da Fase 2), 4 por `backward.*` (roadmap) e 4 pelas duas causas. 8 dos 10 vêm de duas causas conhecidas e corrigíveis. As duas são fail-closed: o erro é de cobertura, não de integridade.
3. **O benchmark achou um bug real da Etapa A.** `set_option X in` seguido de `open … in` (ou de `instance` com nome) ficava vinculado ao arquivo inteiro.
   - Corrigido na Etapa A v5.
   - Teste de regressão permanente: `tests/stage_a/test_stage_a.py::test_set_option_in_binds_through_open_in_and_named_instance`, com 7 casos e 2 mutações no grupo `stage_a`.
