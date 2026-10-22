# Benchmark de enunciados trocados (Fase 1, sub-fase 1b)

```
status: construído (benchmark_version 1); execução no fork (auditor-benchmark) pendente
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

Pendente: primeira execução no fork.
