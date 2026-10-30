# Changelog

Changes that affect auditor users (CLI, `auditor-ci`, workflows, report). Phase 0
was not yet in production when most of these entries were written, so incompatible changes were
made without a transition period.

"Instruction N" refers to the numbered decisions of the project's external reviewer.

## Unreleased

### Phase 1b: swapped-statement benchmark (instructions 24/25)
- `benchmark/` (manifest + 92 Lean files), `tools/phase1/benchmark_*.py` and the `auditor-benchmark` workflow.
- **Result** (`docs/benchmark.md`):
  - no false statement comes out `verified`;
  - cheats that compile: 11/11, with the right reason;
  - false positives on hard correct proofs: 28.6 % (target ≤ 10 %), recorded as L-31.
- **Benchmark finding, a Stage A bug, fixed in v5:** `set_option X in` followed by `open … in`, or by a named `instance`, was bound to the whole file and brought down theorems unrelated to the option. The option now binds to the right declaration; an anonymous instance still has no binding (fail-closed). The policy does not change.
  - Permanent regression test: `test_set_option_in_binds_through_open_in_and_named_instance`.
  - False positives on correct proofs: 34.3 % → 28.6 %.
- **Measurements** move to their own repository, `Enzo47961/auditor-measurements`, because GitHub suspended the fork for heavy Actions usage (`maintenance.md`).

### L-33 (b): tampering detected (Phase 1, instruction 25)
- Stage B ensures the inspector **before** the target's `lake build` and checks, after the build, the hash of the inspector binary and of the installed auditor package. If anything changed, the inspector does not run: `Não resolvida` (unresolved; `toolchain_tampered`), exit 1, not infrastructure.
- `auditor-ci` checks again between files. After tampering, the following files are `not_audited_after_tampering`, `outcome.json` carries `toolchain_tampered: true`, and the summary warns.
- Conformance scenario 11 (tampering with the auditor package; with the inspector binary; a run without tampering, which comes out `Rejeitada` (rejected) under L-33a).

### L-33a: user code executed during elaboration (Phase 1, instruction 24)
- **Stage A v4.**
  - `run_tac` and `by_elab`, in any position: finding `elaboration_code_execution`. Every declaration of the file comes out **`Rejeitada`** (`elaboration_executes_code`, in `policy_violations`).
  - `unsafe` in any position: `Não resolvida` (`unsafe_code`).
- **Inspector v5:**
  - `imports` (import closure);
  - `execution_capable`: constants of the target module whose type reaches `IO.RealWorld`, or that carry `@[extern]`. They leave the file `Não resolvida` (`target_defines_executable_code`).
- **`auditor check --changed <file>`** (repeatable), and `auditor-ci`, which passes the changed files: a changed, imported dependency that executes code during elaboration leaves the target `Não resolvida` (`dependency_executes_code`).
- **Core classification v5:** `show_panel_widgets` leaves `allowed` (it evaluates terms of the file). The core risk classification applies on top of project allow-lists generated earlier.
- Conformance scenarios 09 (execution during elaboration) and 10 (ground truth: `initialize` runs in whoever imports it). Inventory in `docs/l33-inventory.md`; L-17 amended (L-33a); L-30 recorded; note in `phase0-report.md`.
- **Target repositories:** the inspector changes version (the cache is rebuilt); the project allow-list does not need to be regenerated.

### Stage A version 3 (Phase 1, P0-2 (a), instruction 24)
- **Fewer false positives at column 0.** A term continued at column 0 is no longer
  `unknown_command`. Examples: `{ … with }`, `(…)`, `⟨…⟩`, `[…]`, `match`, `let`, `fun`, `do`,
  `for`, `have`, `show`, `from`, `by`, `if`/`then`/`else`, `calc`, `f!`/`s!`/`m!`.
  `add_decl_doc` is accepted at column 0 only right after a `/--` docstring. `cmd%` at column 0
  comes out through the classification, not as unknown.
- **Fewer false `declaration_name_unresolved`:** `.abbrev`, `` `lemma ``, `(lemma := …)` and the
  `class` attribute are not declarations.
- **Guards:** the allow-list generator (core and project) refuses (exit 2) a continuation that is
  a command's initial token in the environment; at run time, Stage A drops any continuation that
  the project has as a command. The core continuations also apply with a project allow-list
  generated earlier (the fork does not need to be regenerated).
- Measured effect (`docs/p0-2-fail-closed.md`): top-60 by fanout from 68.3 % to 65.0 %
  fail-closed; whole of Mathlib from 15.4 % to 14.4 %.
- **Finding recorded, not fixed (L-33):** `run_tac` and `by_elab` execute user code during
  elaboration without Stage A detecting them. Awaiting the reviewer's decision.

### Phase 1 — P0-1 (instruction 24)
- **Measurement over the whole of Mathlib** (run 39845428621):
  - 24,322 of 330,852 declarations (7.35 %) fall only because of a Lean-generated `ctorIdx`;
  - Mathlib does not write any `implemented_by` in source;
  - recorded as L-34, with the TCB policy for generated code in Phase 2.
- Conformance scenario `08-generated-implemented-by`: a Lean-generated `@[implemented_by]`
  (`T.ctorIdx`, `deriving TypeName`) comes out `implemented_by_candidate`, never `verified`.
- Measurement tools in `tools/phase1/` (P0-1 and P0-2) and the fork's `auditor-measure` workflow.

### Phase 0 — closed unconditionally 2026-10-22 (auditor 69ed9cf)
- Unconditional closure confirmed by the reviewer (instruction 24). Auditor `69ed9cf` run in the
  fork, `auditor-base` = `018d7db`; suite **674** passed, 0 failed (run 39825726718); mutation
  **141/141** in 6 groups, 0 survivors (`ci` group 38/38, run 39826324751); step 8 (timeout /
  `auditor-failed-infra`, PR #9) and step 9 (`@auditor report`, PR #8) executed, step 9 with the
  qualified summary (run 39827471933); `auditor-prep` green (run 39826330043);
  `classification_review_status: author-self-review` (L-26) declared in every artifact.
  Evidence in `docs/phase0-report.md`, section "Evidence for the unconditional closure".
- The pending item from the discarded external review is closed (`proposed-improvements.md`).
- **Phase 1 authorized** (not yet started at the time); it starts with the two P0 items of `roadmap.md`. The entry below ("pending steps
  8-9") remains as history, not as status.

### Phase 0 — closed at layer 1 + layer 2 measurement level, author-self-review declared, pending steps 8-9 (2026-10-22)
- Closure declared by the reviewer (instruction 22). Evidence consolidated in `docs/phase0-report.md`:
  3 `warm` PRs on the success path under 5 min (126 s, 130 s, 138 s), fanout probe
  `verified` (`Data/String/Defs.lean`, 9/9), fail-closed path reported separately (PR #7), 662
  tests, mutation 135/135, allow-list byte-for-byte identical, every report with
  `classification_review_status: author-self-review` and `project_dirty: false`.
- **Conditions before Phase 1 opens:** steps 8 (timeout / `auditor-failed-infra`) and 9
  (`@auditor report` on human request) of the layer-2 checklist; the pending item from the
  discarded external review closed (answered or declared unanswered).
- Phase 1 P0 priorities in `roadmap.md`: `@[implemented_by]` generated during elaboration; Stage A
  fail-closed rate (68 % of the 60 files with the highest fanout).

### `auditor-ci` (instruction 23)
- **The summary (Job Summary and the `@auditor report` comment) declares the classification review:**
  a line `classificação: <status> (L-26)`, with the reports' `tcb.classification_review_status`
  (for example, `author-self-review`). With no readable report, `indeterminada (nenhum relatório)`
  (undetermined, no report). Each file in `outcome.json` gains the `classification_review_status` field.

### Workflows (instruction 22)
- **Fix in `auditor-report`:** `@auditor report` answered "no run" for an already-audited commit
  (layer-2 step 9). The `head_sha` filter of GitHub's runs API (used by `gh run list --commit`)
  is not deterministic. The lookup now lists the 100 most recent `auditor-tier1` runs and selects
  the commit on the client. A run in progress gets its own message instead of "infrastructure
  failure". **Target repositories must re-copy the template**
  `ci/templates/auditor-report.yml`.

### Milestone: full validation before measurement (2026-10-22)
- Suite in `ci.yml` (Linux) **633 passed, 0 failed** (`fe95112`). Mutation in 6 groups **125/125**,
  after catching 1 real survivor: `classification_review_status` replaced by a constant.
- `auditor-prep` all green, including `gen_tcb_roots --check` in the fork. The Mathlib allow-list,
  regenerated in CI, came out **byte-for-byte identical** to the committed one (run 39696176700).
- First run (PR #1) and 3 measurement PRs, all under 300 s. Not yet steady state: every new PR
  started `cold` (D-61, below). Reports with
  `classification_review_status: author-self-review` (L-26).

### Documentation (instruction 21)
- **L-27 amended:** the success path of the fanout measurement uses the highest-fanout file whose
  Stage A has no unrecognized item ("no declared syntax" is not enough). File chosen:
  `Mathlib/Data/String/Defs.lean`.
- Phase 1 agenda (`roadmap.md`): 68 % of the 60 highest-fanout files fail in Stage A; an
  `@[implemented_by]` generated during elaboration (`WalkingParallelPair.ctorIdx`) brings down declarations under L-5.
- **Correction to the instruction-20 report:** the 10 `Não resolvida` declarations of the medium PR (#6) are not
  due to declared syntax (the file has no unrecognized item). 8 are due to `set_option backward.*`
  outside the policy and 2 only to `implemented_by_candidate`; identical to those of PR #3.
- `maintenance.md`: reference test for workflows that save a cache (delete, re-run red,
  re-run, re-warm).

### Workflows and `auditor-ci` (instruction 20)
- **D-61: new reusable workflow `auditor-warm-cache`** (template
  `ci/templates/auditor-warm-cache.yml`, triggered by `workflow_dispatch` and push to the base branch).
  It saves the inspector and Mathlib caches on the base branch, with the same keys as `auditor-tier1`.
  A PR only reads caches from its own ref or from the base; without this, every new PR started `cold`.
- **`auditor-ci inspector [--project .] [--check] [--github-output]`:** compiles the inspector without
  auditing anything; with `--check`, it only reports whether it is ready (`built=true|false`). Exit 2 if
  the inspector could not be obtained.
- **A2: `auditor-tier1` saves the inspector cache even when the job is red**, as long as the build
  finished (`actions/cache/restore` + `actions/cache/save` with `always()`). Before, a PR that
  came out `unresolved` never warmed its own cache.
- **D-62: the auditor checkout leaves the workspace after installation** (`$RUNNER_TEMP/auditor-tool`).
  Before, every CI report came out with `project_dirty: true`. The default policy is now read
  from `$RUNNER_TEMP/auditor-tool/policy.toml`.

### Milestone: first end-to-end result (2026-10-21)
- **Layer-2 smoke test passed.** In the fork `Enzo47961/mathlib4` (`auditor-base` on top of
  Mathlib `e1b2403b`), on GitHub Actions, `Mathlib/Logic/Hydra.lean` came out with 20 of 20 declarations
  `Validada`/`Conforme`/`verified`, `exit_code` 0, no unrecognized item, with the Mathlib
  allow-list having no unclassified commands (run 39680033069, auditor `6568835`). It is the project's
  first end-to-end result on a real Mathlib file.
- **Validation state (reference for the measurement PRs):** suite in `ci.yml` (Linux) 609 passed,
  0 failed (`e6e9f62`); mutation in 6 groups 118/118 detected, 0 survivors, 0 skipped.
- **Classification of Mathlib commands: self-review (L-26).** The reports declare
  `classification_review_status: author-self-review`.

### Incompatible
- **Pinned toolchain: `leanprover/lean4:v4.22.0` → `leanprover/lean4:v4.36.0-rc1`** (Mathlib
  `master`'s version on 2026-10-20, commit `e1b2403b`; instruction 12, option X). The v4.22.0 core
  allow-list was removed: a project with another toolchain → `allowlist_unavailable`
  (fail-closed). Inspector `4`; command classification `4`.
- **`auditor check --timeout` removed** (D-36 rejected). The per-file timeout is only
  `--timeout-file`.
- **`auditor-ci run --budget` → `--timeout-total`**, and `--first-run-budget` →
  `--timeout-total-first-run`. Reusable workflow inputs: `budget-seconds` →
  `timeout-total-seconds`, `first-run-budget-seconds` → `timeout-total-first-run-seconds`.
  The names now say what they measure: the PR total (`--timeout-total`) and per file
  (`--timeout-file`).
  - `--timeout-total` (300 s) is **the** PR budget: the 5-min SLA, declared for
    steady state (`cache_state` `warm`/`delta`).
  - `--timeout-total-first-run` (900 s) is **not a second permanent budget**. It is the
    extended budget of a run with a cold cache (`cache_state: cold`), which happens on the
    fork's first run or after the cache is evicted. It applies only with positive evidence
    of a cold cache, and the run declares `first_run: true`. A run that goes past 300 s within it
    does not fail: it gets `cache_cold_extension: true` and the `auditor-first-run` label (D-28;
    `docs/ci.md`; `docs/maintenance.md`, "CI time budgets").
- **`native_decide` never comes out `verified` in Phase 0** (Q9, option a; D-43 confirmed). The
  auxiliary axiom that v4.36 creates per use (`<owner>._native.<tactic>.ax_…`) leaves the premises
  `Não resolvido` (`native_auxiliary_axiom`). The O-1 justification remains mandatory (without it,
  `Não conforme`), but it is not enough.
- **The toolchain's TCB roots become `target_trusted_roots`** (D-42, D-47). Before, they were all
  of the toolchain's top-level `.olean` files. Now they are only the roots the target project actually
  uses, measured on Mathlib's import closure at the pinned commit (`e1b2403b`, checked against
  `lake-manifest.json`): `Init`, `Lake`, `Lean` and `Std`. `LakeMain`, `Leanc`, `LeanChecker`,
  `LeanExport` and `LeanIR` are no longer TCB: an `@[extern]`/`@[implemented_by]` from them comes out
  `unresolved`. File: `src/auditor/data/target_trusted_roots/` ("roots whose modules are
  implicitly trusted in the target project's closure", not "all roots of Lean's TCB");
  generator: `tools/gen_tcb_roots.py`. In the Stage B report, `boundary.toolchain_roots` became
  `boundary.trusted_roots`, and `boundary.declared_roots` lists everything the toolchain declares.
  A target project other than Mathlib generates its own file (L-21).

- **Project allow-list: target libraries only** (D-52). `auditor-gen-allowlist` extracts the
  commands only from the `lean_lib`s marked `@[default_target]` in the lakefile (or those given with
  `--lib`, repeatable), and no longer from every `.olean` of the build. With none, an error (exit 2). The
  generated file gained the `libraries` field. Reason: in Mathlib, `lake exe cache get` builds the
  `Cache` library, which defines `Lean.Name.fromComponents` as `Mathlib.Lean.Name`; the two cannot
  be imported together, and the generator failed. `generator_version` `2` → `3`.
- **Line endings normalized in the `lake-manifest.json` hashes** (D-53). `env_pin` (project
  allow-list), `tools/gen_tcb_roots.py` and `tools/layer2/fanout.py` compute the hash with CRLF → LF:
  the same commit gives the same value in a Windows clone (`core.autocrlf=true`) and on Linux. SHA-256 of
  the normalized content, not git's blob hash (SHA-1, D-18). `ENV_PIN_VERSION` `1` → `2`:
  project allow-lists generated earlier become `allowlist_stale` and must be regenerated.
  `target_trusted_roots` regenerated: `lake_manifest_sha256` `c9b51d72…` (CRLF clone) →
  `f77f47db…` (the repository's); the rest is identical.
- **`gen_tcb_roots.py --check` accepts a measurement fork** (D-54, L-24): `HEAD` ≠ recorded commit only
  if the recorded commit is an ancestor and the tree differs only in `.github/`, with no `.lean` file.
- **Pinned runner: `ubuntu-24.04`** (D-55) in the reusable workflow, in `ci.yml` and in the
  `auditor-label`/`auditor-report` templates. GitHub has been migrating `ubuntu-latest` to Ubuntu 26 since
  2026-10-19, and the layer-2 measurement cannot switch images midway. Updating the pinned
  actions (Node 20, which GitHub already forces to run on Node 24) is left for a separate round, outside
  layer 2, recorded here.

- **Stage A: header `module` and symbol commands** (D-56, D-57; `stage_a_version` `2`).
  `module` (v4.36's module system, the first line of every Mathlib file) is accepted as the
  file's first token; in any other position, it remains `unknown_command`. Risky commands
  whose token is a symbol (`?`, `$`) are only looked for at the start of a command: before, every `?_` in
  `refine ⟨?_, ?_⟩` became `syntax_extension_declared`. Reserved words (`macro`, `#eval`, …)
  are still detected in any position. New conformance fixture: `07-module-header`.

- **Report: schema `1.1.0`, mandatory field `tcb.classification_review_status`** (L-26).
  A project classification (`.auditor/classification.toml`) now requires consistent `reviewed_by` and
  `reviewer_independence` (`revision_note` optional); without them, `auditor-gen-allowlist`
  exits with code 2. The generated allow-list gains `classification_review` (`generator_version` `4`). The
  classification's SHA-256 uses normalized line endings, like the manifest's (D-53).
- **`gen_tcb_roots.py --check` in a fork also accepts `.auditor/`** (D-59, L-24): the allow-list and the
  classification that step 3 of the checklist commits in the fork. Still: no `.lean` file, ancestry.

### Mathlib paths that changed
- **`Mathlib/Logic/Basic.lean` no longer exists** at the pinned commit (`e1b2403b`). The equivalent is
  `Mathlib/Basic/Logic/Basic.lean` (8072 dependents, position 24 in fanout). No auditor script,
  fixture or test references the old path. Only `docs/ci.md` and the layer-2 checklist
  cited it, and both were updated. The layer-2 tools (`fanout.py`)
  check the checkout's commit (`--expect-commit`), so they do not point to a file from
  another commit.
- **`auditor-ci-outcome/2`** (instruction 11): `exit_code`, `cache_state`, `first_run`,
  `cache_cold_extension`, clock since the trigger. Version 1 is rejected by
  `label-decision` (resulting in `auditor-failed-infra`).

### Added
- Per-file timeout (`--timeout-file`, 90 s) that ends the PR's audit (exit 2).
- PR wall-clock budget since the trigger, including preparation; `cache_state`;
  extended budget with a cold cache; `auditor-first-run` label.
- `tools/layer2/` (fanout and timings per `cache_state`); `docs/layer2-checklist.md`.
- `fanout.py` records provenance (checkout commit, SHA-256 of `lake-manifest.json`,
  `lean-toolchain`) and accepts `--expect-commit`. The JSON output became
  `{"provenance": …, "rows": […]}`.
- `tools/layer2/native_usage.py`: the share of declarations that use native evaluation
  (`native_decide`, `+native`, `native := …`, `bv_decide`), counted with Stage A's lexer.
- Actions pinned by commit SHA; elan from a pinned release with a checked SHA-256.

### Security
- The inspector imports the environment without loading extensions (`loadExts := false`): it does not run
  code from the imported modules, including the PR's (D-39).
- `unlock_limits` (new in v4.36) is recorded by Stage A as the `set_option … 0`s it applies,
  and the `set_option` policy decides (D-41).
