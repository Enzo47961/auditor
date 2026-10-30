# Maintenance

The Stage A allow-list, the inspector, mutation tests and version pinning in the workflows.

"Instruction N" refers to the numbered decisions of the project's external reviewer.

## What is maintained, and by whom

The allow-list has two parts of different origin:

| Part | Origin | File |
|---|---|---|
| Command list | **extracted mechanically** from the toolchain (the parser's `command` category, via `src/auditor/lean/Dump.lean`) | generated in `src/auditor/data/allowlist/<toolchain>.json` |
| Risk classification (`syntax_extension`, `metaprogramming`) and continuation tokens | **maintained by hand**, with a written criterion | `tools/gen_allowlist/classification.toml` |

An extracted command that is not classified falls into `allowed`. That is why, **when bumping the toolchain, every new command needs human review**: the generator lists what changed, but it does not judge the risk.

## Staleness test

`tests/maintenance/test_allowlist_fresh.py` runs `gen.py --check`: it runs the extractor with the pinned `lean-toolchain` and fails if the versioned file does not match exactly. The generator also fails if `classification.toml` cites a command that does not exist in the toolchain, so that the classification does not rot when Lean removes syntax.

At run time, Stage A selects the allow-list by the **target project's** `lean-toolchain`. Without a file for that toolchain, the result is `allowlist_unavailable` (fail-closed). An allow-list whose content declares another toolchain is rejected.

## Procedure when bumping the toolchain

It is the procedure for every Mathlib bump. It was executed end to end in the bump
`v4.22.0 → v4.36.0-rc1` (instruction 12); the notes "On the bump to v4.36" record what each
step found.

1. **Pin the target version.** Read Mathlib's `lean-toolchain` at the chosen commit and note the
   commit. Install: `elan toolchain install <toolchain>`.
2. **Update `lean-toolchain`** at the root and in every fixture (`git ls-files | grep lean-toolchain$`;
   `test_fixture_toolchain_matches_root` points out divergent copies).
3. **Allow-list extractor.** Run `python tools/gen_allowlist/gen.py`. If `Dump.lean` does not
   compile, adapt it to the new API. *On v4.36: `String.trim` → `trimAscii`; `importModules
   (loadExts := true)` started requiring `enableInitializersExecution` (accepted only in the generator; see
   `docs/tcb.md`, D-39).*
4. **Classify the new commands.** The generator lists what changed and refuses a classification that cites
   a nonexistent command. A new unclassified command falls into `allowed`, so **each one** goes through the
   criterion of `classification.toml` (L-17), reading its definition in the toolchain's source. When in doubt,
   fail-closed. A command whose effect is equivalent to a policy option (e.g. `unlock_limits`) is
   recorded by Stage A as that option. Bump `classification_version`. *On v4.36: 40 new
   commands and 1 removed (`set_premise_selector`); classification `4` (D-40, D-41).*
5. **Remove the previous toolchain's allow-list.** The auditor only supports the tested toolchain; an
   allow-list without a matching inspector and suite would be an unverified promise.
6. **Inspector.** Compile it (`stage_b.ensure_inspector`) and adapt it to the new API. Compare
   the new toolchain's `src/lean/Lean/Util/CollectAxioms.lean` with `directDeps` in `Inspect.lean`
   (the independent closure must mirror the official walk). Check that the inspector still
   does not run imported code (`loadExts := false`). Bump `inspectorVersion` and
   `INSPECTOR_VERSION` together. *On v4.36: `CollectAxioms.collect` became private and started using
   axioms precomputed in the `.olean` files; an axiom's type started being walked; docstrings
   read with `findInternalDocString?` (raw text); `@[simp]`/`@[ext]` read from the modules'
   entries.*
7. **Run the whole suite** and treat each failure as a sign that Stage A or B depended on a
   version detail. Separate what is a mechanical change (names, API) from what changes the meaning of a
   result: the second kind is a policy decision, goes to the reviewer, and in the meantime the
   behaviour is fail-closed. *On v4.36: `native_decide` started adding one axiom per use
   (L-19, Q9); the owner convention for `where` changed (L-4).*
8. **TCB boundary.** The TCB roots are each toolchain's `target_trusted_roots`
   (`src/auditor/data/target_trusted_roots/<toolchain>.json`): the roots the target project actually uses,
   **not** all the ones the toolchain declares (D-42). Regenerate with Mathlib at the pinned commit
   and the dependencies at the exact revisions of its `lake-manifest.json`:
   `python tools/gen_tcb_roots.py --sysroot <sysroot> --project <mathlib> --root Mathlib`.
   The generator checks each package against the manifest (commit = `rev`) and refuses on a mismatch. The
   canary `test_06_tcb_boundary_canary` checks the list declared by the toolchain, and scenario
   `06-tcb-boundary` has one declaration per root of the allow-list (`uses_<root>`) that must come out
   TCB. A new or removed root goes to review by someone other than the author (`docs/tcb.md`, (ii)).
   *On v4.36: the toolchain started declaring `LeanChecker`, `LeanExport` and `LeanIR`; Mathlib's
   closure uses only `Init`, `Lake`, `Lean` and `Std` (D-42, D-47).*
9. **Ground truth.** `tests/conformance/test_ground_truth.py` runs Lean's own `#print axioms`
   on the fixtures. Update only what Lean now prints differently, never the verdict on the
   false statements (the negations still compile).
10. **Mutation.** Run `python tools/mutation/run.py <group>` **one group at a time**, in this order:
    `stage_a`, `allowlist`, `stage_b`, `policy`, `ci`. Check for 0 survivors and commit
    between groups. If the process is interrupted midway, `git status` shows the file that
    was left mutated: restore it with `git checkout -- <file>` before anything else. The
    `policy` group is the heaviest, because it runs the conformance suite for each mutation.
11. **Record.** `CHANGELOG.md` (incompatible: pinned toolchain), README ("Environments"),
    `docs/tcb.md` (roots), and the new decisions in `docs/proposed-improvements.md`.
12. **Review.** Command classification, the TCB boundary and any change of verdict require
    review by someone other than the author.

## CI time budgets (D-21, D-28, D-36)

Three limits, with names that say what they measure (D-36):

| Limit | CLI | Workflow input | Default | What it is |
|---|---|---|---|---|
| PR total | `auditor-ci run --timeout-total` | `timeout-total-seconds` | 300 s | **The** budget: the 5-min SLA, in steady state (`cache_state` `warm`/`delta`). Clock from the trigger, preparation included. |
| PR total with a cold cache | `auditor-ci run --timeout-total-first-run` | `timeout-total-first-run-seconds` | 900 s | **The extended budget of a run with a cold cache**, not a second permanent budget. It only applies with positive evidence of `cache_state: cold`, which happens on the fork's first run or after the cache is evicted. A missing signal counts as a warm cache. |
| Per file | `auditor check --timeout-file` / `auditor-ci run --timeout-file` | `timeout-file-seconds` | 90 s | The limit for one file; exceeding it ends the PR's audit (exit 2). |

A run with a cold cache declares `first_run: true`. If it goes past 300 s without exceeding 900 s, it does not
fail: it gets `cache_cold_extension: true` and the `auditor-first-run` label. Layer-2 measurements
never use a `cold` run as steady state (`docs/layer2-checklist.md`, step 7). Changing a
default is an SLA change: it goes to the reviewer and into `CHANGELOG.md`.

## Confusables table (TR39)

`src/auditor/data/unicode/confusables-16.0.0.txt` is a versioned copy of Unicode TR39 16.0.0 (terms of use in the file's header). Updating the version is an explicit change: a new file with the new version in its name, and the path updated in `stage_a.py`.

## Project allow-list (Mathlib and others)

Commands defined by a project or by its dependencies (Mathlib defines `lemma`, `alias`, `assert_not_exists`, …) are not in the core allow-list. To audit files of such a project:

1. In the already-built project (in Mathlib: `lake exe cache get`), run `auditor-gen-allowlist --project <dir>`. The generator runs `lake build` on the target libraries (the lakefile's `@[default_target]` `lean_lib`s, or those given with `--lib`; D-52), imports all their modules, extracts the commands and writes `<dir>/.auditor/allowlist.json` with the `env_pin` (`lean-toolchain` + `lake-manifest.json`).
2. Read the `unclassified` list of the generated file: these are the project's new commands. While they are there, they are fail-closed.
3. Classify each one in `<dir>/.auditor/classification.toml` (keys `classification_version`, `allowed`, `syntax_extension`, `metaprogramming`), with the same criterion as `tools/gen_allowlist/classification.toml`. The classification may not cite core commands or nonexistent commands; the generator refuses.
4. Regenerate. `--check` fails if the file does not match the current environment.
5. Classification is policy: it requires review by someone other than the author.

`env_pin` uses `lake-manifest.json` with normalized line endings (D-53): a CRLF clone and an LF clone of the same commit give the same pin. When `lake-manifest.json` or `lean-toolchain` changes, the allow-list becomes stale and Stage A fails closed (`allowlist_stale`) until it is regenerated.

**The Mathlib allow-list is layer-2 evidence**, generated in the maintainer's fork. It does not block layer 1, whose requirement is the generator tested against an arbitrary Lake project (`tests/allowlist`). Phase 0 does not check the semantic correctness of the classification, only the match with the pin (L-16).

## Stage B inspector

The inspector (`src/auditor/lean/Inspect.lean`) is compiled with the target project's toolchain and cached (`%LOCALAPPDATA%\auditor\inspector` on Windows, `$XDG_CACHE_HOME/auditor` or `~/.cache/auditor` elsewhere; `AUDITOR_CACHE` overrides). The cache key is the hash of source + toolchain, so any change to the inspector produces a new binary.

When changing `Inspect.lean`, bump `inspectorVersion` and `INSPECTOR_VERSION` (`stage_b.py`) together; a test locks against divergence.

The dependency walk mirrors the pinned toolchain's `Lean.CollectAxioms.collect`. When bumping the toolchain:
1. compare the new toolchain's `src/lean/Lean/Util/CollectAxioms.lean` with `directDeps` in `Inspect.lean`;
2. run `tests/stage_b`. The tests compare the inspector with `#print axioms` and lock the conventions on which attribution depends.

## Naming convention for `native_decide` auxiliaries

Attributing `native_decide` to the owning declaration depends on the compiler's `X._proof_N` convention (L-4). It is locked by regression tests in `tests/stage_b` (`test_05_owner_attribution`, `test_edges_where_auxiliary_owned_by_top_level_declaration`, `test_edges_private_declaration_reported_and_owned`). A toolchain bump must pass them.

## Mutation tests

A green test is only evidence if it turns red when the code is wrong. This discipline has already found real failures twice: a false mutation result caused by pytest's `pythonpath` (Stage A) and 4 test holes in the Policy, all fixed. It does not depend on memory: the catalog and the runner are versioned.

- **Catalog:** `tools/mutation/catalog.py`. Groups `stage_a`, `allowlist`, `stage_b`, `policy`, `ci` and `gen_tcb_roots` (the latter since instruction 15); each mutation is (file, original snippet, mutated snippet), and each group declares the tests that must catch it.
- **Runner:** `python tools/mutation/run.py [group ...]`. It applies each mutation, runs the group's tests with `-x`, and restores the file from an in-memory copy, also on error. It ends with exit 1 if any mutation **survived** (a hole in the tests) or was **skipped** (pattern not found).
- **Catalog integrity:** `tests/maintenance/test_mutation_catalog.py`, fast and part of the normal suite, fails if any pattern stops occurring exactly once in the code. That way, refactoring a check forces updating the corresponding mutation, instead of it silently becoming a "skipped" mutation.

**When to run:**
1. when closing each stage;
2. when changing any policy rule (a rule change requires an audit by another person, and the mutation result is part of that audit's evidence);
3. when bumping the toolchain.

**When adding a new check,** add at least one mutation that turns it off and confirm that it is detected. A surviving mutation is resolved by writing the missing test, never by removing the mutation.

**Pitfalls already encountered:**
- pytest with `pythonpath = ["src"]` imports the repository's code. Mutating a copy in another directory makes every mutation falsely "survive"; the runner mutates in place.
- Strings with backslashes in scripts generated through a shell heredoc lose their escaping; the catalog uses *raw* strings in a Python file.
- **A process killed from outside does not restore the file.** Restoration on error covers exceptions, not a process terminated by the system (out of memory, instruction 12). After an interruption, `git status` shows the mutated file; check the diff (it must be exactly one catalog mutation) and restore it with `git checkout -- <file>`. That is why mutation runs one group at a time, with a commit between groups.

**Run log** (one line per group; commit between groups):

| Date | Code commit | Group | Detected | Survivors / skipped |
|---|---|---|---|---|
| 2026-10-20 | `0b9d2bc` (v4.36.0-rc1) | `stage_a` | 9/9 | 0 |
| 2026-10-20 | `0b9d2bc` | `allowlist` | 9/9 | 0 |
| 2026-10-21 | `0b9d2bc` | `stage_b` | 16/17 | **1 survivor**: `.axiomInfo v => v.type.getUsedConstants` → `#[]` (the closure did not walk an axiom's type in any fixture). New test: `edges`, `via_axiom_type` (reaches `sorryAx` only through the type of `ax_over_sorry`). The mutation, re-run alone, was detected (`inspector_disagreement`). Result: 17/17. |
| 2026-10-21 | `064f170` | `policy` | 45/45 (36 earlier + 9 from the roots allow-list, D-42) | 0 |
| 2026-10-21 | `6532f5e` | `ci` | 22/22 | 0 |
| 2026-10-21 | `6532f5e` | `stage_b` (re-run on the final code) | 17/17 | 0 |

| 2026-10-21 | `b73bc6d` (rename to `target_trusted_roots`) | `policy` | 45/45 | 0 |
| 2026-10-21 | `b73bc6d` | `stage_b` | 17/17 | 0 |

After the rename (`b73bc6d`), the whole suite gave 558 passed. `ci` has not changed since `6532f5e`.

The `stage_a` and `allowlist` groups were run on `0b9d2bc`. Their code and tests did not change up to `6532f5e` (empty `git diff --stat`), so the result holds for the final code. **State on 2026-10-21: 5 groups, 115/115 detected, 0 survivors, 0 skipped.** The whole suite, run in parts, gave 558 passed and 0 failures.

**Instruction 15 (layer 2: D-52, D-53, D-54).** From here on, mutation and the suite run on GitHub Actions (Linux, `ubuntu-24.04`), not on the maintainer's machine. Mutation uses the measurement fork's `auditor-mutation` workflow; the suite uses this repository's `ci.yml`, on every push.

| Date | Code commit | Group | Detected | Survivors / skipped |
|---|---|---|---|---|
| 2026-10-21 | `2a4306b` | `allowlist` (9 earlier + 4: D-52 and D-53) | 13/13 | 0 |
| 2026-10-21 | `2a4306b` | `gen_tcb_roots` (new group: D-53 and D-54) | 8/8 | 0 |

Mutation run: `Enzo47961/mathlib4`, run 39665194703 (5 min 21 s). The `stage_a`, `stage_b`, `policy` and `ci` groups were not re-run: their code has not changed since the commits recorded above.

**Suite on Linux** (`ci.yml`, run 39664969425 on `2a4306b`): 585 passed, **3 failed**. The 3 failures already happened at `bcdccc6` (run 39655475487: 555 passed, 3 failed), the suite's first run outside Windows, and do not come from the instruction-15 changes. They are machine-dependent tests (L-23):
- `tests/stage_b/test_stage_b.py::test_timeout_is_not_success` and `tests/cli/test_cli.py::test_artificial_timeout_never_success` ask for a 0.01 s timeout, but Stage B applies a 1 s floor (`max(1.0, …)` in `stage_b.analyze`). On the runner, the fixture compiles in under 1 s, and the timeout does not fire (`success`). It is not fail-open: the build finished within the effective limit.
- `tests/ci/test_ci.py::test_all_pass` expects `cache_state: warm`, but on a runner without an inspector cache, the first run comes out `cold`.

Fixing these tests depends on the reviewer's decision (instruction 15: nothing new in the auditor until the next `auditor-prep`).

**Instruction 16 (D-56, D-57, D-58).** The 3 tests were fixed (D-58): the two timeout tests use a generated fixture (`conftest.slow_lean_source`, 800 theorems by `decide`, ~13 s on Windows), which takes seconds to compile on any machine, and check that the measured duration went past 1 s; `test_all_pass` warms the inspector cache first (`ci._prebuild_inspector`) and declares that it tests the warm path. **The `ci.yml` suite (Linux) is the layer-1 reference**; the local run is a convenience.

| Date | Code commit | Group | Detected | Survivors / skipped |
|---|---|---|---|---|
| 2026-10-21 | `e6e9f62` | `stage_a` (9 + 4: D-56, D-57) | 13/13 | 0 |
| 2026-10-21 | `e6e9f62` | `allowlist` (re-run: `stage_a.py` changed) | 13/13 | 0 |
| 2026-10-21 | `e6e9f62` | `stage_b` (tests changed: D-58) | 17/17 | 0 |
| 2026-10-21 | `e6e9f62` | `policy` (includes `tests/cli`, which changed: D-58) | 45/45 | 0 |
| 2026-10-21 | `e6e9f62` | `ci` (tests changed: D-58) | 22/22 | 0 |

Run: `auditor-mutation`, run 39671405280 (20 min, Linux): 110/110. Suite in `ci.yml` (run 39670595679 on `e6e9f62`): **609 passed, 0 failed**. The `gen_tcb_roots` group (8/8 at `2a4306b`) was not re-run: its code and tests did not change. **State on 2026-10-21: 6 groups, 118/118 detected, 0 survivors, 0 skipped.**

| Date | Commit | Group | Detected | Survivors |
|---|---|---|---|---|
| 2026-10-21 | `382b5a5` | `stage_a` | 13/13 | 0 |
| 2026-10-21 | `382b5a5` | `allowlist` (+10: D-52/D-53, L-26) | 18/19 | **1** |
| 2026-10-21 | `382b5a5` | `stage_b` | 17/17 | 0 |
| 2026-10-21 | `382b5a5` | `policy` | 45/45 | 0 |
| 2026-10-21 | `382b5a5` | `ci` (timeout tests with the slow fixture) | 22/22 | 0 |
| 2026-10-21 | `382b5a5` | `gen_tcb_roots` (+1: D-59) | 9/9 | 0 |

Run: `auditor-mutation`, run 39694466059 (31 min, Linux): 124 detected, **1 survivor**, 0 skipped. Suite in `ci.yml` (run 39694408989 on `382b5a5`): **627 passed, 0 failed**. Survivor: `classification_review_status` replaced by the constant `"author-self-review"` (`src/auditor/tier1/stage_a.py`). The tests only covered the self-reviewed classification, and a constant equal to the only tested value passed. A test gap, not a code gap. Fixed with `test_classification_review_status_values` (the 6 paths: `core-only`, `no-project-classification`, `undeclared` without a declaration and with a null `reviewed_by`, `human-reviewed`, `independent-ai-reviewed`). Checked locally: with the mutation applied, 4 of the 6 cases fail. Re-run on `fe95112` (run 39698136489): `allowlist` **19/19**, 0 survivors. Suite in `ci.yml` (run 39698083967 on `fe95112`): **633 passed, 0 failed**. **State on 2026-10-22: 6 groups, 125/125 detected, 0 survivors, 0 skipped.** The fork stays on auditor `382b5a5`: from `382b5a5` to `fe95112` only a test and this document changed.

**Instruction 20 (D-61, A2, D-62).** Affected groups re-run on `7f7238d`:

| Date | Commit | Group | Detected | Survivors |
|---|---|---|---|---|
| 2026-10-22 | `7f7238d` | `ci` (+10: D-61, A2, D-62) | 32/32 | 0 |
| 2026-10-22 | `7f7238d` | `allowlist` | 19/19 | 0 |
| 2026-10-22 | `7f7238d` | `stage_b` | 17/17 | 0 |

Run: `auditor-mutation`, run 39758578127 (Linux): 68 detected, 0 survivors, 0 skipped. Suite in `ci.yml` (run 39758445713 on `7f7238d`): **662 passed, 0 failed**. The `stage_a`, `policy` and `gen_tcb_roots` groups were not re-run: from `fe95112` to `7f7238d` their code and tests did not change (`git diff --stat` only touches `ci.py`, a comment in `allowlist.py`, workflows, CI tests and docs). **State on 2026-10-22: 6 groups, 135/135 detected, 0 survivors, 0 skipped.**

**Instruction 22 (step 9: `auditor-report`).** The `ci` group re-run on `7ba9b6f` (+3 mutations in the `auditor-report.yml` template): **35/35**, 0 survivors, 0 skipped (`auditor-mutation`, run 39821051965). Suite in `ci.yml` (run 39820617451 on `7ba9b6f`): **666 passed, 0 failed**. The other groups have not changed since the commits recorded above. **State on 2026-10-22: 6 groups, 138/138 detected, 0 survivors, 0 skipped.**

**Instruction 23 (the `classificação: … (L-26)` line in the summary).** The `ci` group re-run on `69ed9cf` (+3 mutations: removing the summary line, not recording the per-file field, replacing "indeterminada" (undetermined) with a fixed value): **38/38**, 0 survivors, 0 skipped (`auditor-mutation`, run 39826324751). Suite in `ci.yml` (run 39825726718 on `69ed9cf`): **674 passed, 0 failed**. **State on 2026-10-22: 6 groups, 141/141 detected, 0 survivors, 0 skipped.**



## Reference test for the cache workflows (A2, instruction 21)

A cache that always hits does not test the path that saves. With the base branch warmed (D-61), every PR restores the inspector from the base and A2's save step never runs. **Every workflow that saves a cache is tested like this, when created or changed:**

1. Delete the cache in question on the base's ref (`gh api -X DELETE repos/<fork>/actions/caches/<id>`; list them with `gh api repos/<fork>/actions/caches`). Only caches that `auditor-warm-cache` can regenerate.
2. Re-run a PR whose job comes out **red** (`gh run rerun <run>`). Expected: miss, build, red job, and still the save step `success`; the cache appears with ref `refs/pull/N/merge`.
3. Re-run again. Expected: `inspector: hit` in `outcome.json`.
4. Re-warm the base (`gh workflow run auditor-warm-cache --ref auditor-base`) and check that the caches are back on `refs/heads/auditor-base`.

Reference run (2026-10-22, auditor `7f7238d`): the base's inspector cache deleted (id 9332096105); PR #6 (`Connect.lean`, exit 1) re-run (run 39760129710): attempt 2 built and saved on `refs/pull/6/merge`; attempt 3 `inspector: hit`, `warm`, 125.2 s; base re-warmed (run 39761275384).

## Reference tests for the CI failure modes (steps 8 and 9, instruction 22)

**Step 8: infrastructure timeout.** On a branch of the fork, add `timeout-file-seconds: 5` to the `with:` of `auditor-tier1.yml` and touch a `.lean` file whose audit takes longer than that (`Mathlib/Logic/Hydra.lean`, ~13 s). Open the PR and never merge it. Expected and verified (PR #9, run 39818035267, auditor `7f7238d`):
- file `timeout`, `timeout_kind: file`, `duration_s` 5.54 with `timeout_s` 5;
- `exit_code: 2`, `infra_failed: true`, `audit_failed: false`, `timeout_aborted: true`;
- `cache_state: warm`, i.e. the timeout is not confused with a cold cache;
- job **green**, PR `mergeable` (not blocking);
- label `auditor-failed-infra` (not `auditor-first-run`);
- no comment on the PR.

**Step 9: `@auditor report`.** The fork's owner comments `@auditor report` on an already-audited PR. Expected: a single `github-actions` comment with the summary, starting with "Pedido por um humano" (requested by a human). First run (PR #8, run 39818084000, 2026-10-22): **failed**. It answered "no run for commit `769e23c`", although run 39813522377 existed and had completed. Cause: the `head_sha` filter of the runs API (used by `gh run list --commit`) is not deterministic. The same query, repeated, alternated between 0 and 1 result on all three endpoints (`/actions/runs`, `/actions/workflows/<file>/runs`, `/actions/workflows/<id>/runs`). It does not depend on the `gh` version: 2.101.0 and 2.103.0 gave both results. Fix in the `auditor-report.yml` template: list without a server-side filter and select the commit on the client; a run still in progress has its own message, instead of "infrastructure failure". Checked against the fork (PRs #1, #5, #8, #9, three times each). A test and 3 mutations in the `ci` group. **Second run** (auditor `7ba9b6f`, fork `465d97e`; PR #8, run 39821013448): a single `github-actions` comment, starting with "Pedido por um humano (`@auditor report`). Commit `769e23cba36b`", with the summary of run 39813522377 (9 `verified`, `warm`, 137.6 s). The request is recorded under the account of whoever commented (OWNER). **Third run, with the qualified summary** (auditor `69ed9cf`, fork `018d7db`): PR #8 was closed and reopened to produce an audit with the new auditor (run 39826300196: `warm`, 135.6 s, 9 `verified`). The `@auditor report` (run 39827471933) posted a single comment, with the line `classificação: author-self-review (L-26)` right below the correspondence notice.

Not tested in layer 2: a comment from someone **without** access to the repository does not trigger the job. It would require a second account. The guarantee is the job's `author_association` condition, locked by `test_report_workflow_requires_explicit_human_request`.

## Updating the summary of an old run without changing the PR (instruction 24)

Situation: the auditor changed (for example, the summary gained a new line) and a measurement PR needs a report produced by the new auditor, without changing the PR's code.

- **Do not use `gh run rerun`.** A re-run executes the workflow of the original commit, with the old auditor SHA, and reproduces the old summary.
- **Close and reopen the PR** (done by the maintainer, `gh pr close N` and `gh pr reopen N`). The `reopened` event (one of `pull_request`'s default types) triggers `auditor-tier1` from the PR's merge ref. On a PR that does not touch `.github/`, the merge ref's workflow is the base's, with the new auditor SHA. Result: a new audit, without a commit on the PR.
- Check in the new run's `outcome.json` that the auditor is the expected one and that the summary carries the change. Only then ask for `@auditor report`, which reads the commit's most recent run.

Reference run (2026-10-22, auditor `69ed9cf`, fork `018d7db`): PR #8 closed and reopened; new audit run 39826300196 (`warm`, 135.6 s, 9/9 `verified`, `classification_review_status: author-self-review`); `@auditor report` run 39827471933, with the line `classificação: author-self-review (L-26)`. Approved by the reviewer in instruction 24.

## Version pinning in the workflows (D-25)

**Every action in the auditor's workflows is pinned by SHA; an update is a PR that changes the SHA and is reviewed.** This applies to this repository (`.github/workflows/`) and to the target repository's templates (`ci/templates/`). A tag is mutable; a commit SHA is not. If an action's publisher is compromised, a floating tag is a supply-chain attack vector, exactly the kind of silent swap the auditor exists to detect.

- Format: `uses: actions/<name>@<40-hex SHA> # vX.Y.Z`. The comment with the version is mandatory and serves the review; `tests/ci/test_workflows.py` requires both.
- To update: get the commit SHA of the new tag (`git ls-remote --tags https://github.com/actions/<name>`; for an annotated tag, use the `^{}` line), change SHA and comment together, read the action's changelog and open a PR. The reviewer checks the SHA against the tag.
- **elan:** `elan-init.sh` downloads elan's `latest` release, so pinning the script's tag does not pin elan (D-35). The workflows download the binary of the pinned release (`ELAN_VERSION`) and check `ELAN_SHA256` before running it. To update: download `elan-x86_64-unknown-linux-gnu.tar.gz` from the new release, compute the SHA-256, change both values in `ci.yml` and `auditor-tier1.yml` in the same PR.
- What is not pinned by hash in CI (L-18): the Lean toolchain that elan downloads from `lean-toolchain`, and the Python dependencies resolved by pip. Their effective versions enter the report's TCB (`kernel.githash`, `aggregator.python_dependencies`).

**Phase 1, instruction 24 (P0-2 (a), L-33a).** The 6 groups were re-run on `a0e3387`:
- 10 new Stage A v3 mutations (continuations, `add_decl_doc`, `cmd%`, a declaration keyword out of position, the generator's guard);
- 18 for L-33a (`run_tac`/`by_elab`, including removing `run_tac` from the list, as requested by the reviewer; `unsafe`; inspector v5's `execution_capable` and `imports`; `--changed`; core risk over an old allow-list).

Result: **169/169 detected, 0 survivors, 0 skipped** (`auditor-mutation`, run 39851946124). Suite in `ci.yml` (run 39851133711 on `a0e3387`): **778 passed, 0 failed**.

A round on `d5f6264` was **cancelled**: two tests were already failing without any mutation (a fixture that did not compile and an outdated Stage B contract, fixed in `aa3d552`). With a broken test, every mutation of the group would look detected.

**State on 2026-10-22: 6 groups, 169/169.**

**Practice (instruction 25): mutation only runs on a green suite.** A round on a red suite is discarded, not interpreted: with a test already failing, every mutation of the group looks detected, and the number becomes noise. Before dispatching `auditor-mutation`, check that `ci.yml` is green for the same commit. Example: the round on `d5f6264` was cancelled and redone on `a0e3387`.

**L-33 (b), instruction 25.** The 6 groups were re-run on `a18d131`, with the suite green (run 39861318092, 788 passed). There are 5 new mutations for (b): the auditor package hash, the inspector hash, stopping the inspector when there is tampering, `toolchain_tampered` in the report and the between-files check in `auditor-ci`. Result: **174/174 detected, 0 survivors, 0 skipped** (`auditor-mutation`, run 39862103829). **State on 2026-10-22: 6 groups, 174/174.**

## Measurements repository (2026-10-23)

**Change.** On 2026-10-23 GitHub suspended the workflows of the fork `Enzo47961/mathlib4` for heavy Actions usage:
- two runs were cancelled with SIGTERM midway: benchmark 39876032952 and mutation 39876502155;
- the following ones stayed queued without a runner;
- the maintainer re-enabled the workflows.

**Heavy measurements run in a dedicated repository; the fork keeps the measurement PRs and the PR workflows** (approved in instruction 26). **So as not to depend on GitHub's tolerance towards forks**, the heavy workflows moved to a dedicated, public, **non-fork** repository: [`Enzo47961/auditor-measurements`](https://github.com/Enzo47961/auditor-measurements).
- **Workflows:** `auditor-mutation`, `auditor-prep`, `auditor-measure` and `auditor-benchmark` (later also `auditor-study`).
- **Mathlib:** each one downloads the official Mathlib (`leanprover-community/mathlib4`) at the pinned commit `e1b2403b`, overlays the repository's `.auditor/` (the same allow-list and classification as the fork) and checks the commit before running.
- **What stays in the fork:** the layer-2 measurement PRs (#1 to #9) and the PR workflows (`auditor-tier1`, `auditor-label`, `auditor-report`, `auditor-warm-cache`). The runs cited up to this date were in the fork.

**First run in the new repository:** `auditor-prep` green (run 39879622234, auditor `81457ac`):
- Mathlib commit `e1b2403b`;
- allow-list regenerated byte-for-byte identical;
- `gen_tcb_roots --check` with exit 0;
- smoke test 20/20.

**Load rule (instruction 25, after the suspension):**
- mutation only on the groups affected by the change; a full round only when closing a sub-phase;
- benchmark and measurements only when the benchmark or the auditor change in a relevant way;
- no whole-Mathlib measurement without need.

**Stage A v5 (binding of `set_option … in`).** The `stage_a` group re-run on `81457ac`, with the suite green (run 39876002319, 800 passed): **30/30** (28 + 2 new), in the measurements repository's `auditor-mutation` (run 39879882456). The other groups have not changed since `a18d131` (174/174). **State on 2026-10-23: 6 groups, 176/176.**
