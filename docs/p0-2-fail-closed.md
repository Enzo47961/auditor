# P0-2 — Stage A fail-closed rate (Phase 1, sub-phase 1a.2)

```
status: in progress — (a) done; kill criterion met (L-30); (b) awaits L-33a (done) and the official re-measurement; (c) re-measured after (a)
```

Classification: `author-self-review` (L-26). No number in this document is a claim of Mathlib coverage to third parties. "Instruction N" refers to the numbered decisions of the project's external reviewer.

## 1. Method

- **Tool:** `tools/phase1/stage_a_causes.py`. It runs the same `stage_a.analyze` as CI, with the fork's project allow-list, on the first `--top` files of the `tools/layer2/fanout.py` ranking, and classifies each unrecognized item into one of four causes:
  - **(a)** false positive: `unknown_command`;
  - **(b)** non-syntactic command: `metaprogramming_command` or `unclassified_command`;
  - **(c)** syntax: `syntax_extension_declared`;
  - **(d)** other cause.
- **Input:** fork `auditor-base` `018d7db`, which is Mathlib `e1b2403b` plus `.github/` and `.auditor/` (allow-list with 259 commands, `author-self-review`). Fanout ranking with provenance `e1b2403b`, manifest SHA-256 `f77f47db…`, `leanprover/lean4:v4.36.0-rc1`.
- **Populations:**
  - the 60 files with the highest fanout (the reviewer's gate);
  - **additionally**, the 8651 files of the `Mathlib` library. The extra measurement does not replace the gate; section 4 explains why it matters.
- Local run (Windows), deterministic for the same checkout and the same allow-list. Raw data kept in the maintainer's working directory (`p0/`: `causes60*.json`, `causes_all*.json`).

## 2. Results

| Population | Before (Stage A v2) | After (a) (Stage A v3) |
|---|---|---|
| Top-60 by fanout | 41/60 fail-closed (**68.3 %**) | 39/60 (**65.0 %**) |
| Whole `Mathlib` library | 1333/8651 (**15.4 %**) | 1244/8651 (**14.4 %**) |

Distribution of causes in the top-60. A file may have more than one cause; the "only this" column counts the files that fixing that cause alone would recover.

| Cause | Before: files | Before: only this | After (a): files | After (a): only this |
|---|---|---|---|---|
| (a) false positive | 3 | 1 | 0 | 0 |
| (b) non-syntactic | 21 | 7 | 21 | 7 |
| (c) syntax | 32 | 17 | 32 | 18 |
| (d) other | 2 | 1 | 0 | 0 |

After (a), the 39 top-60 files that fail split as follows: 18 only because of syntax, 7 only because of a non-syntactic command, and 14 for both reasons.

- **Non-syntactic commands in the top-60** (files): `initialize` 15, `register_option` 5, `run_cmd` 3, `with_weak_namespace` 2, `register_linter_set` 1, `register_simp_attr` 1, `register_label_attr` 1, `declare_core_config_elab` 1, `simproc_decl` 1.
- **Syntax in the top-60** (files): `syntax` 21, `elab` 7, `macro` 6, `prefix`, `elab_rules`, `infixl`, `infixr`, `notation`, `macro_rules` 4 each, `declare_syntax_cat` and `notation3` 2 each, `binder_predicate`, `infix` and `postfix` 1 each.
- **Whole of Mathlib, after (a)** (files with the cause / only with it):
  - (a) false positive: 44 / 29;
  - (b) non-syntactic: 230 / 120;
  - (c) syntax: 1090 / 969;
  - (d) other: 8 / 2.

  The dominant syntax is `notation` (553 files), followed by `syntax` (163), `infixl` (123), `notation3` (111) and `elab` (102).

## 3. (a) False positives: what changed (Stage A version 3)

Stage A treated every token at column 0 as the start of a command. Measured over the whole of Mathlib before the fix: 167 files with `unknown_command`, 112 of them only because of it. There were four causes:

1. **A term continued at column 0.** Examples: `{ … with }`, `(…)`, `⟨…⟩`, `match`, `let`, `fun`, `f!"…"`, `do`, `for`.
   - These tokens were added to `continuation` (`tools/gen_allowlist/classification.toml`).
   - The term words from the reviewer's list that are **not** commands were also added: `have`, `show`, `from`, `by`, `if`, `then`, `else`, `calc`, `s!`, `m!`.
   - From the reviewer's list, `end`, `section`, `namespace`, `open`, `variable` and `universe` were **not** added: they are real commands and are already accepted as commands. Putting them in `continuation` would be wrong, and the guard below would refuse it.
2. **`add_decl_doc` after a docstring.** The syntax is `docComment >> "add_decl_doc " >> ident` (`Lean/Parser/Command.lean:939`). The initial token is the docstring, so `add_decl_doc` at column 0 is the command's second token. The new `doc_continuation` list accepts it **only** right after a `/--` docstring. This case explained 82 files.
3. **`cmd%` at column 0** (for example, `compile_inductive%`). The column-0 check used the key without the `%`. The file remains fail-closed, but now through the right classification (`metaprogramming_command`), not as `unknown_command`.
4. **A declaration keyword outside a declaration position.** It produced `declaration_name_unresolved` in four patterns, none of which starts a declaration:
   - `.abbrev`, `.opaque` and `.structure`: a constructor or field;
   - `` `lemma ``: a name literal;
   - `(lemma := …)`: a named argument;
   - `[class]` and `@[class, …]`: the `class` attribute.

**Guards.** A continuation can never be a command's initial token:
- `check_continuations` (`src/auditor/allowlist.py`) makes the core and project generators refuse (exit 2) a continuation that is a command in the environment;
- at run time, Stage A drops any continuation that the project has as a command.

Checked on the pinned toolchain and on the Mathlib allow-list: no collision.

Risk detection does not change: a risky command is still detected in any position, including after a continuation (test `test_continuation_does_not_hide_risky_commands`).

**Residue of (a), kept fail-closed on purpose:**
- bare identifiers at column 0 (`Eq.symm`, `rfl`, `X`…): there is no safe lexical rule that tells them apart from an unknown command;
- `@[…]` items that break the line (`deprecated`, `+typeChanged`);
- declaration keywords inside quotations (`def $id …`), in files that already declare syntax;
- ProofWidgets JSX (`<span class=…>`).

Over the whole of Mathlib, 44 files with a false positive remain, 29 only with it.

**Tests:** 9 new tests (22 cases) in `tests/stage_a`. **Mutations:** 10 new ones in the `stage_a` group, 23/23 detected locally (the official run is the fork's `auditor-mutation`, after the push).

## 4. The ceiling of what (b) can recover, and the kill criterion

In the top-60, 32 files declare syntax. Instruction 24 keeps genuine syntax fail-closed. Therefore:
- relaxing **all** non-syntactic commands, including `run_cmd`, the best case is 28 clean files and 32/60 = **53.3 %** fail-closed;
- without relaxing `run_cmd` (2 of the 7 files that fail only because of non-syntactic commands: `Mathlib/Init.lean` and `Mathlib/Basic/FunLike/Basic.lean`), the best case is 34/60 = **56.7 %**.

**So the P0-2 kill criterion (> 50 % after (a) and (b)) is already met**, whatever the reading of (b). Under instruction 24: Phase 1 continues, but the claim of "Mathlib coverage" is blocked until Phase 2. The < 30 % target is unreachable in this population without relaxing syntax.

**Note on the population (it does not change the gate).**
- The top-60 by fanout is largely infrastructure: 36 of the 60 are in `Tactic/`, `Lean/` or `Util/`, and 25 of those 36 fail. These files declare syntax by design.
- Outside those folders, 14 of 24 fail. They are `Defs`/`Notation`/`Logic` files, almost all because of `notation`/`infix`.
- Over the whole of Mathlib, the rate is 14.4 %. The dominant cause is `notation` (553 files).
- `notation`/`infix` generate macros that run during elaboration. Under L-17 they are fail-closed, but the code is **generated by the toolchain**, like P0-1's `ctorIdx`.
- Relaxing them would change the syntax policy: that is the reviewer's decision, not this sub-phase's.

## 5. (b) Non-syntactic commands: reading started and STOPPED

Reading at the pinned commit, so far:

| Command | Reading | Situation |
|---|---|---|
| `run_cmd` | executes code | **kept fail-closed** (instruction 24) |
| `initialize` | `Lean/Compiler/InitAttr.lean`: `[init]` procedures "are run in the files that IMPORT the file where they are defined"; `runInitAttrForMod` walks only the imported modules. It does not execute during the elaboration of its own file | candidate for `allowed` under the L-17 criterion; **not applied** (see below) |
| `register_option`, `register_simp_attr`, `register_label_attr`, `register_linter_set` | expand to `initialize` (to be confirmed case by case in the source) | pending |
| `simproc_decl` | declares a simproc that a later `simp` in the SAME file executes | probably stays fail-closed; pending |
| `with_weak_namespace`, `declare_core_config_elab` | pending | pending |

**Why we stopped.** The reading of (b) depends on the L-17 criterion: a command is fail-closed if it can execute code during elaboration, before Stage B. Testing that criterion exposed a contradiction in the Phase 0 architecture (`limitations.md`, L-33). Stage A **does not detect** `run_tac` (a tactic) or `by_elab` (a term), and both execute user code during the elaboration of their own file, including IO.
- Demonstrated in a throwaway project: both wrote a marker file during `lake build`.
- The complete auditor gave `verified` and exit 0 on both files.

L-17 covers only commands. The defence against pre-audit execution, which is what justifies treating `initialize` and the others with care, has an open path through tactics and terms. Relaxing commands on the basis of that defence before deciding what to do about the open path would be the wrong order. The decision is the reviewer's (instruction 24, "when to stop and ask": a Phase 0 contradiction exposed by Phase 1).

## 6. Pending

- The reviewer's decision on the finding of section 5 (L-33).
- Resume (b) case by case, with a no-effect test for each relaxation.
- Re-measure (c) in the fork, with the official measurement on GitHub Actions.
- ~~L-30~~ recorded (instruction 24): 65.0 % after (a); ceiling 53.3 %; Mathlib coverage blocked until Phase 2.

## 7. The reviewer's answer (instruction 24) and the confirmed sequence

- **A met kill criterion is a correct result.** Recorded as L-30, without dressing up the number. The 14.4 % rate of the whole library is recorded separately. The dominant cause (toolchain-generated `notation`) becomes a question for Phase 2.
- **L-33 (question 1), option (c) approved:**
  - (a) was applied (L-33a, `docs/l33-inventory.md`);
  - (b), hashing the inspector and the auditor, is a Phase 1 item.
- **The sequence for P0-2's (b) (question 2), confirmed:**
  - resume only after L-33a;
  - `register_option`, `register_*_attr` and `register_linter_set` by the same reading as `initialize`;
  - `run_cmd` and `simproc_decl` kept fail-closed.
- **The reviewer's requirement on `initialize`, confirmed by execution (scenario 10):**
  - (1) it does not execute during the elaboration of its own file;
  - (2) it executes when the file is imported.

  So `initialize` in a dependency is an execution vector. Stage A does not see the dependency, and L-33a's lexical crossing only covers `run_tac`/`by_elab`.
  - **Decision:** `initialize` is **not** reclassified as `allowed`, not even in the target. In the target, L-33a's environment rule already flags it (the procedure is an `IO …` constant).
  - Relaxing it only makes sense after mitigation (b) or after extending the dependency crossing to registered code.
  - The same holds for `register_option`, `register_*_attr` and `register_linter_set`, which expand to `initialize`.
  - The ceiling of (b) in the top-60 therefore drops to the files that fail only because of `simproc_decl`/`run_cmd`/`with_weak_namespace`/`declare_core_config_elab`, all kept fail-closed or still unread. Result: **(b) recovers no top-60 file in this phase.**

## 8. Official re-measurement on GitHub Actions

| Measurement | Run | Stage A | Top-60 | Whole of Mathlib |
|---|---|---|---|---|
| after (a) | [39845428621](https://github.com/Enzo47961/mathlib4/actions/runs/39845428621) (auditor `aa5750b`) | v3 | 39/60, **65.0 %** | 1244/8651, **14.4 %** |
| after L-33a | [39849624202](https://github.com/Enzo47961/mathlib4/actions/runs/39849624202) (auditor `d5f6264`) | v4 | 39/60, **65.0 %** | 1282/8651, **14.8 %** |

Both measurements agree with the local one. Fork `afd92f7`; no `.lean` file differs from `e1b2403b`.

- **Top-60:** Stage A v4 does not change the rate. The 2 files with `unsafe` already failed because of syntax or of a command.
- **Whole of Mathlib:** lexical `unsafe` appears in 74 files, and is the only cause in 40 of them. Hence the rise from 14.4 % to 14.8 %. The data are kept in the maintainer's working directory (`p0/measure2/`).

**Not included in these numbers:**
- `run_tac`/`by_elab`: a finding (`Rejeitada`, rejected), not an unrecognized item. There are 2 Mathlib files (`run_tac`), and only one of them, `NumberTheory/Bertrand.lean`, was clean.
- **L-33a's environment-based detection** (a target constant whose type reaches `IO.RealWorld`, or that carries `@[extern]`): it only appears when auditing each file with the inspector. **Not measured over the whole of Mathlib here**; measured later as L-35 (`limitations.md`).
