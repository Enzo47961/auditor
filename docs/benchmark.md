# Swapped-statement benchmark (Phase 1, sub-phase 1b)

```
status: measured (benchmark_version 1); false-positive target not met → L-31
classification: author-self-review (L-26)
```

Goal (instruction 24): show whether the auditor finds the errors that matter, not only that it works on correct proofs. The metrics are **per category, never aggregated**. The benchmark is a sample, not a proof of universal coverage.

"Instruction N" refers to the numbered decisions of the project's external reviewer.

## 1. Population (instruction 25)

- **Success path:** files of the `Mathlib` library (`e1b2403b`) that Stage A accepts. They are 7369 of 8651 (85.2 %) in the official measurement with Stage A v4 (run 39849624202).
  - Infrastructure folders are left out: `Tactic/`, `Lean/`, `Util/`, `Mathport/`, `Deprecated/`, `Testing/`. 7184 files remain.
  - It is **not** the top-60 by fanout: that set is structurally fail-closed (L-30; 32 of the 60 declare syntax by design). The whole library is the real universe.

## 2. Categories

| Category | Cases | Construction | Expected |
|---|---|---|---|
| **Hard correct proofs** (`correct_hard`) | 35 | Mathlib's own theorems, audited in their original file, without copying. Deterministic selection (`tools/phase1/benchmark_select.py`, `benchmark/selection.json`), detailed below | `verified` |
| **Swapped statements** (`swapped_statement`) | 24 | A real Mathlib lemma with its statement altered and the original proof, which no longer applies: `<` for `≤`, a hypothesis removed, `∃` for `∀`, domain ℕ for ℤ, a stronger conclusion, a swapped operation | not `verified` (`compile_failure`) |
| **Validity controls** (`swap_control`) | 24 | The **original** statement of each swap, with the same proof | `verified` |
| **`sorry` and axioms** (`sorry_axiom`) | 11 | **False** statements (the same as the swaps) "proved" by a cheat that compiles: `sorry` (4), a custom `axiom` (3), a lying `@[implemented_by]` + `native_decide` (2), `run_tac` + `sorry` (1) and a `sorry` three imports below the target (1) | not `verified`, with the cheat's reason |
| **Inconclusive** (`inconclusive`) | 6 | A **correct** proof in a file with something that Stage A or the policy does not recognize: `macro`, `notation`, `syntax` + `macro_rules`, `unsafe`, `set_option backward.*`, an identifier at column 0 | `unresolved`, with the fail-closed reason |

**Selection of the correct proofs:**
- a deterministic sample of 800 files (ordered by the SHA-256 of the path);
- non-private `theorem`/`lemma` with a proof of at least 15 lines;
- at most one per file and 4 per area, round-robin;
- 23 areas.

## 3. Independent ground truth (instruction 24, principle 6)

- Every negative case has a **formal proof of the negation** (`benchmark/lean/GroundTruth/`), checked by the kernel. It is always a concrete instance, with `decide`/`norm_num`.
- The ground truth itself is audited and must come out **`verified`**. A ground truth with `sorry`, an axiom or native evaluation would invalidate the case.
- **Validity rule.** A negative case only counts if:
  1. the ground truth came out `verified`;
  2. for a swapped statement, the control (original statement, same proof) also came out `verified`.

  Without the control, a wrong lemma name would make the swapped case "not compile" for the wrong reason. Invalid cases are listed and excluded, never counted as detections.
- The `implemented_by` + `native_decide` cheats prove a finite instance of the false statement. Its falsity is that of the ground truth of the originating swap (S03, S14).
- The hard correct proofs have no ground truth of their own: they are Mathlib theorems, and Mathlib compiles at the pinned commit.

## 4. Metrics

Computed by `tools/phase1/benchmark.py report`, per category:
- **validity:** valid cases / cases;
- **sensitivity** (negative categories): valid cases that did not come out `verified`. A **false negative** (a valid negative that is `verified`) is listed separately: it is the catastrophic error;
- **right reason:** the alert carries one of the expected codes (for example `sorryAx_detected` for `sorry`);
- **false-positive rate** (positive categories): correct proofs that did not come out `verified`, with the codes of each;
- **precision:** alerts on negatives / total alerts (negatives + positives).

**Targets of instruction 24:**
- detect ≥ 50 % of the swapped statements with a formal ground truth;
- ≤ 10 % false positives on the correct proofs.

If they are not met, the result becomes **L-31**, with the real rate and the causes.

## 5. What this benchmark measures, and what it does not (an honest record before the numbers)

- **A swapped statement with the original proof:** detection is guaranteed by construction. If the statement is false (formal ground truth), no honest proof compiles, and the file comes out `compile_failure`.
  - This category measures that the auditor **does not emit `verified` for a file that does not compile**. It does not measure the ability to find the error.
  - A sensitivity of 100 % here is expected and says little. Below 100 % would be a serious bug.
- **The real test of the auditor is the `sorry_axiom` category:** false statements that **compile**, because they cheat. This measures whether the auditor detects and classifies the cheat.
- **Correspondence remains unaudited** (L-9). A statement swapped for something **true** (weaker) and proved honestly would come out `verified`. That is out of scope and not in the benchmark, because the ground-truth rule requires a false statement.
- **Sample bias:** the negative cases use elementary lemmas (ℕ, ℤ, ℝ, `Finset`, `List`), because the ground truth must be formal and checkable. The hard correct proofs cover the heavy areas.
- **Difficulty:** "hard" is approximated by proof length, not by a measure of difficulty.
- **False positives on the correct proofs** are already partly predictable, from L-34 (generated `ctorIdx`, 7.35 % of declarations) and from L-33a (executable code in the target). The benchmark measures how much of this appears in this sample.

## 6. Execution

- **Where:** the fork's `auditor-benchmark` workflow (dispatch, `auditor-ref`).
- **Steps:**
  1. `lake exe cache get`;
  2. copy `benchmark/lean/` into `Mathlib/AuditorBenchmark/`, on the runner only (no `.lean` file of the base branch changes);
  3. `benchmark.py run`: each file cited by the manifest (cases, controls, ground truths), audited once by the real auditor;
  4. `benchmark.py report`.
- **Files generated** by `tools/phase1/benchmark_build.py`, deterministically.
- **Checks:** `tests/maintenance/test_phase1_tools.py` tests the computation of the metrics (validity, sensitivity, false negatives, precision) and the consistency of the manifest.

## 7. Results

### 7.1 Runs

| Run | Where | Auditor | Situation |
|---|---|---|---|
| 1st (run 39865083826) | fork | `5562afd` | 7 invalid cases: a ground truth or control did not compile (narrow imports; wrongly named lemmas); P32 not found (made private by the module system) |
| 2nd (run 39868546708) | fork | `c2d64de`… | with build logs: confirmed the causes; the swapped statements fail with a type mismatch (22/24), an invalid projection (S22) and an instance (S17, invalid) |
| 3rd (run 39872741098) | fork | `c2d64de` | **100 valid cases**: reference measurement, Stage A v4 |
| 4th (run 39876032952) | fork | `81457ac` | cancelled by GitHub (SIGTERM): the fork's workflows were suspended for heavy usage |
| 5th (run 39879879325) | `auditor-measurements` | `81457ac` | **100 valid cases**: Stage A v5, official Mathlib at commit `e1b2403b` |

The errors of the 1st and 2nd runs were the benchmark builder's, not the auditor's:
- imports too narrow under the module system;
- `native_decide` requires `public meta import` (case C09);
- matching of the private name.

The invalid cases were excluded, not counted as detections.

### 7.2 Metrics per category

| Category | Valid | 3rd: Stage A v4 | 5th: Stage A v5 |
|---|---|---|---|
| Hard correct proofs: false positives | 35 | 12 (**34.3 %**) | 10 (**28.6 %**) |
| Controls (original statement): false positives | 24 | 0 | 0 |
| Swapped statements: sensitivity / false negatives | 24 | 100 % / 0 | 100 % / 0 |
| Cheats that compile: sensitivity / right reason / FN | 11 | 100 % / 11 / 0 | 100 % / 11 / 0 |
| Inconclusive: `Não resolvida` (unresolved) with the expected reason | 6 | 6 | 6 |
| Alert precision (negatives / total) | — | 0.745 | 0.778 |

**Between the 3rd and the 5th runs, Stage A v5 started binding `set_option … in` through `open … in` and to a named `instance`.** The policy did not change.
- The finding came from the benchmark itself: the unbound option became a whole-file effect and brought down theorems that had nothing to do with it.
- Both numbers are recorded.

### 7.3 Remaining false positives (5th run)

| Cause | Cases | Pending |
|---|---|---|
| Generated `ctorIdx` only (`implemented_by_candidate`, L-34) | P03, P05 | Phase 2 P0 (structural recognition) |
| `set_option` outside the policy only | P12, P14, P26, P29 | the options `backward.isDefEq.respectTransparency`, `…types` and `backward.defeqAttrib.useBackward` applied to the theorem **itself**; P29 is an anonymous instance, with no binding by design. Relaxing `backward.*` is on the roadmap, with a no-effect test |
| Both causes | P02, P08, P25, P28 | both of the above |

**Reading:**
- **No false statement came out `verified`** in 35 valid negative cases. The 11 cheats that compile were detected, all with the right reason.
- **The false positives are all fail-closed**, with a known and recorded cause (L-34; the `set_option` policy). None comes from a detection error.
- **The controls' simple proofs come out 24/24 `verified`.**
- **The coverage cost lies in real Mathlib proofs,** in heavy areas: algebraic geometry, category theory, algebraic topology.

### 7.4 Against the targets of instruction 24

- **Detection ≥ 50 % of the swapped statements:** 100 %, but **by construction** (section 5). The number that measures the auditor is that of the cheats: 11/11, with the right reason 11/11.
- **≤ 10 % false positives on the correct proofs: not met, 28.6 %.** Recorded as **L-31**.
- **Kill criterion** (detection < 20 % and FP > 30 %): not met. Detection is total and FP stays below 30 %.
- **Advancement criterion** (detection ≥ 50 % with FP ≤ 10 %): also not met, because of FP.

### 7.5 Closure record (instruction 26)

**1b closed with L-31 recorded.** The three points of the record:
1. **The number that measures the auditor is 11/11 on the cheats that compile**, with the right reason and zero false negatives. The 100 % detection of swapped statements is **by construction**: a false statement does not compile.
2. **The 28.6 % false positives break down as follows:** 2 from `ctorIdx` (L-34, Phase 2 P0), 4 from `backward.*` (roadmap) and 4 from both causes. 8 of the 10 come from two known, fixable causes. Both are fail-closed: the error is one of coverage, not of integrity.
3. **The benchmark found a real Stage A bug.** `set_option X in` followed by `open … in` (or by a named `instance`) was bound to the whole file.
   - Fixed in Stage A v5.
   - Permanent regression test: `tests/stage_a/test_stage_a.py::test_set_option_in_binds_through_open_in_and_named_instance`, with 7 cases and 2 mutations in the `stage_a` group.
