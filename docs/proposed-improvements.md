# Recorded objections to the specification

Recorded **before** implementation. Changes require explicit authorization.

"Instruction N" refers to the numbered decisions of the project's external reviewer. Status values (`Validada`, `Rejeitada`, `Não resolvida`, `Conforme`, `Não conforme`, `Não resolvido`, `Não auditada`) are quoted as the tool prints them; see the README for their meaning.

## O-1. `native_decide` justification — RESOLVED: option (B)

**Decision:** a docstring with the strict grammar, no escaping, no multiple lines; any deviation is a violation. Scenario 05 includes the multi-declaration drift. Option (C) is recorded as a fallback in `limitations.md` (L-4), conditional on a real objection from Mathlib, with no preventive migration.

**Problem.** The `@[auditor_justified]` attribute (item 3) only exists if it is registered in an imported module. Mathlib will not depend on the auditor's package, so the decided mechanism is inapplicable to the main target. The initial classification of this objection as "not substantive" was wrong.

### Investigation (toolchain `leanprover/lean4:v4.22.0`, commit `ba2cbbf0`)

**(A) Attribute silently ignored without the package: DOES NOT WORK.**

```
A.lean:2:2: error: unknown attribute [auditor_justified]
A2.lean:2:21: error: unexpected identifier; expected prio     ← form with arguments
```

An unregistered attribute is an elaboration error, and the form with arguments does not even get past the parser. There is no "optional" attribute mechanism.

**(B) Docstrings in the elaborated environment: WORKS.**

A lake project with `Fix/Target.lean` compiled to `.olean`. A separate inspector imports the module via `importModules` and reads with `findDocString?`, without access to the source text:

```
justified   | doc=some "Lema sobre ordem.\nauditor_justified: reason=\"kernel decide too slow\" reviewer=\"@enzo\" "
unjustified | doc=some "Docstring comum, sem justificativa. "
nodoc       | doc=none
```

Attributing `native_decide` to the owning declaration, by name:

```
referência direta a Lean.ofReduceBool: justified._proof_1_3, unjustified._proof_1_3, nodoc._proof_1_3
'consumer' depends on axioms: [Lean.ofReduceBool]   ← consumer uses justified; inherits transitively
```

Algorithm: for each audited declaration, find in its dependency closure the constants that reference `Lean.ofReduceBool`/`Lean.ofReduceNat` directly. For each one, resolve the owning declaration by removing the internal components of the name (`justified._proof_1_3` → `justified`) and require a justification in the owner's docstring. In the example, `consumer` is covered because its only source is `justified`, which is justified. If some owner is not justified, the violation is attributed to it and propagated to its dependents.

### Assessment of (B) against the three objections of item 3

- **(a) "Comments do not exist in the elaborated environment".** Docstrings do: they are stored in the `.olean` and Stage B reads them directly. Stage A takes no part.
- **(b) "Matching by position breaks under refactoring".** There is no matching by position: the docstring belongs to the declaration by name, in the environment.
- **(c) "A docstring on the wrong declaration and nobody notices".** It is noticed: if the justification is on another declaration, the owner of the `native_decide` is left without one, and the result is a violation (fail-closed).

### Residual risks of (B)

1. **The naming convention for auxiliaries (`X._proof_N`) is a compiler implementation detail** and may change between Lean versions. Mitigation: if resolving the owner does not find a non-internal declaration, the result is `Não resolvida` (unresolved) with reason `native_decide_owner_unresolved`. The convention enters the staleness test of `docs/maintenance.md`.
2. **The docstring appears in Mathlib's generated documentation.** I do not know whether Mathlib reviewers accept a visible structured line in docs. Not testable here.
3. **Forgery.** Any author can write the line. The attribute had the same property; approval remains human and out of scope.
4. **Strict grammar.** A line `auditor_justified: reason="…" reviewer="@handle"` with strict parsing. A malformed line is a violation, not ignored.

### Recommendation

Adopt (B). It answers the three objections of item 3 with evidence, works without a dependency in the target project and is fail-closed by construction. Since it reverses an explicit decision (item 3 rejected docstrings), **I await authorization**. If (B) is rejected, I will present the trade-offs of (C).

Investigation fixtures: kept, to become regression tests for the rule.

## O-2. The `maxHeartbeats 0` exemption depends on Stage A

`set_option` is not recorded in the elaborated environment; condition (b) can only be matched syntactically. Mitigation: only the form `set_option maxHeartbeats 0 in <declaration>` is eligible for the exemption (the `in` binds the option to the following declaration, without matching by position). The file-level or section-level form is never exemptable.

## O-3. `maxHeartbeats 0` as `Rejeitada` — RESOLVED

Implemented as decided: `Rejeitada` (rejected), reason `set_option_violation`, only on the declaration that uses the option. A dependent declaration is evaluated on its own merits (option i) and may be `Validada` + `Conforme`; the dependency appears in the `depends_on_rejected: [names]` field of schema v1.

## O-4. Warnings have no field in the spec's schema

Item 5 introduces warnings (confusables). An optional `warnings` field (a list) per declaration and at the report level. It is additive and does not change mandatory fields.

## Q1–Q3 — RESOLVED

- **Q1:** (X) strictly orthogonal, plus `overall_status` (`verified` only if both states are positive). Applied in every test.
- **Q2:** scenario 03 was rescoped to an unknown axiom (`03-axiom-unknown`): `Não resolvido` + `unknown_axiom`.
- **Q3(a):** `g_zero` → `Não resolvida`, `implemented_by_candidate`.
- **Q3(b):** an orphan justification → violation `orphan_justification`.

### Notes on the application (for veto)

- **R-1. The coverage described in Q2 does not match (X).** Q2 describes scenario 02 as "forbidden in a dependency, via sorryAx". By table (X), `sorryAx` affects only `proof_status`, and the premises are evaluated without it: 02 tests transitive admission, not the "forbidden" category in the premises. That category is covered by 05 (`Lean.ofReduceBool` without justification → `Não conforme`). A forbidden axiom that is neither `sorryAx` nor `ofReduceBool` will only be covered by the policy's regression tests. I implemented the table literally.
- **R-2. `orphan_justification` goes to `proof_status: Rejeitada`.** Derivation: the spec defines `Rejeitada` as "a concrete policy violation demonstrated", and (X) reserves `premises_status` for dependencies.

## Q4–Q6 — RESOLVED

- **Q4:** precedence `rejected` > `unresolved` > `verified` ("the worst state wins"). Formalized as a table in the README; it enters schema v1 in the Schema step.
- **Q5:** a project allow-list generated by `auditor-gen-allowlist --project <dir>`, bound to the environment pin; a stale allow-list is fail-closed. Layer-1 tests against a minimal Lake project (`tests/allowlist`). The Mathlib allow-list is layer-2 evidence. Semantic correctness of the allow-list is Phase 1+ (L-16).
- **Q6:** a target that does not compile → exit 1, `proof_status: Não resolvida`, `overall_status: unresolved`, reason `compile_failure`.

## Local decisions taken in Stage A (for veto)

- **D-1. Risk classification of commands** (`tools/gen_allowlist/classification.toml`). Fail-closed when the command introduces syntax, executes arbitrary code capable of changing the environment, is internal to the core, or hides content (`#exit`). `#eval` and `run_cmd` are fail-closed; `unif_hint`, `grind_pattern` and `#check` are allowed.
- **D-2. Confusables rule:** detection by pairs (TR39 §4) within the file, ignoring single-character components (L-6). Warning about every confusable character would fire on almost every Mathlib file (α→a, ι→i, ℝ→R).
- **D-3. Structure:** scenarios as project directories; the package in `src/auditor/` (standard Python layout), not in `src/main.py`.

## O-5. `@[extern]` — ACCEPTED
It enters the spec in the same risk category as `@[implemented_by]`. Scenario `04b-extern` created, with the same ground-truth format as 04: (a) the attribute alone; (b) combined with `Lean.ofReduceBool`. The ground truth derives `False`: a user `@[extern "lean_nat_add"]` on a definition that multiplies. The fixture needs `precompileModules := true`, because the interpreter only evaluates a user `extern` if the module defining it has native code loaded. The policy rules for `extern` depend on Q7.

## Q7 — RESOLVED: option (a), with a boundary specification

Toolchain implementations are TCB. The boundary is declared by the toolchain (library roots in `<sysroot>/lib/lean`) and by `lake-manifest.json` (user roots), not by the module name. Algorithm, guarantees and maintenance are in `docs/tcb.md`, section "TCB boundary"; unit tests in `tests/tcb`. The canary is scenario `06-tcb-boundary`, and `04b-extern` gained case (c).

**Change in the inspector (v2).** The inspector no longer decides `in_toolchain`. It now emits only facts: the real path of each module's `.olean`, the sysroot, the effective search path and the docstrings of all owners. The TCB/user decision lives in Python, testable without Lean.

## D-1 to D-3 — ACCEPTED

- **D-1, with the reviewer's addition.** `#reduce` became fail-closed, like `#eval`; before, it **was not covered** (it fell into `allowed`). Applying the same criterion ("evaluates → fail-closed"), I checked in the toolchain's source that `#guard` and `#widget` call `evalExpr`, the same execution of compiled code as `#eval`; both also became fail-closed. `classification_version` went up to 2. Tests: `tests/stage_a/test_stage_a.py::test_risky_commands`.
- **D-2** and **D-3:** no change.

## Q8. Commands that only reduce — RESOLVED (see "Instruction 10 round"; original question below)

By the D-1 criterion, `#reduce` (reduction) was treated like `#eval` (execution). Other core commands also reduce terms without executing compiled code: `#guard_expr` (with `=~`, defeq), `#check_simp` (runs `simp`), `#synth` (instance resolution), `#check_tactic` (runs a tactic). They remain `allowed`. Question: is the reviewer's criterion "executes code" (so only `#reduce` is an explicit exception) or "evaluates/reduces" (so all four also become fail-closed)? Without an answer, I keep them `allowed`. Changing it is one line in `classification.toml`.

## D-4 to D-10 — full details for review

None is urgent for the Policy: the Policy was implemented without depending on a veto of them. If any is vetoed, the change is local.

### D-4. Project allow-list pin
- **What it does.** `env_pin = SHA-256(pin version ‖ lean-toolchain ‖ bytes of lake-manifest.json)`, with each part prefixed by its length (`src/auditor/allowlist.py::env_pin`). The project allow-list stores this value. Stage A recomputes the pin from the current environment and only uses the allow-list if the values match.
- **What changes in behaviour.** Any change to the toolchain or to any byte of the manifest (a dependency version, even whitespace) makes the allow-list stale: `allowlist_stale`, Stage A does not use the list and the report exits with exit 2. The **project's own source does not enter** the pin. If it did, the Mathlib allow-list would become stale with every commit, and in practice would be regenerated on every audit, which is the dynamic allow-list rejected in Q5(b). Consequence recorded in L-16: a new project command falls into `unknown_command` (fail-closed); a redefined command keeps the old classification.
- **How it is tested.** `tests/allowlist/test_project_allowlist.py`: the pin equals the recomputed one; the manifest changed in one byte, or the `toolchain`, `env_pin` or `kind` field tampered with → `allowlist_stale`; `--check` detects the drift. End to end: `tests/cli/test_cli.py::test_stale_project_allowlist_is_infra` (exit 2, no `verified`). Mutations: removing the pin comparison and removing the manifest from the hash are detected.

### D-5. Classification of project commands
- **What it does.** The generator splits the extracted commands into core commands (classified by `tools/gen_allowlist/classification.toml`) and new project commands. The new ones only leave `unclassified` if they are in `<project>/.auditor/classification.toml`. The generator refuses (exit 2) a classification that: cites a nonexistent command; cites a core command (a project cannot reclassify `#eval` as allowed); classifies a command twice; or has an unknown key.
- **What changes in behaviour.** An unclassified project command → `unclassified_command` in any position → declarations `Não resolvida`. In the core, the default for a command without a listed risk is `allowed`, because the criterion was applied to all 122 extracted commands. In the project, the default is fail-closed, because nobody has looked at the new commands.
- **How it is tested.** `tests/allowlist`: `my_lemma` without a classification → `unclassified_command`; with a classification → accepted; the four kinds of invalid classification → exit 2. Mutations: making `unclassified` empty, turning off the stale-command, duplicate and unknown-key checks are detected.

### D-6. Project modules in the extraction
- **What it does.** The generator runs `lake build` in the project and imports **all** the `.olean` files in `<project>/.lake/build/lib/lean`, plus `Lean`. The extracted commands are those of that entire environment.
- **What changes in behaviour.** The allow-list covers every command available in any file of the project, not only in files that import everything. A command defined in a module that the target does not import is on the allow-list, but it cannot appear in the target without the import (Lean would not recognize it), so the effect is nil. A project without a build → an explicit error.
- **How it is tested.** `tests/allowlist`: the command `my_lemma`, defined in `Mini.Cmd`, appears in the generated allow-list; a project without `lake-manifest.json` → exit 2.

### D-7. Running the inspector
- **What it does.** `Inspect.lean` is compiled as an executable with the target project's toolchain, in a cache folder outside the repository. The cache key is the hash of the inspector's source + toolchain + lakefile. The executable runs under `lake env` at the project root, to inherit the pinned `LEAN_PATH`.
- **What changes in behaviour.** The first audit with a new toolchain takes about 15 s more (compilation); later ones reuse the binary. Any change to the source produces a new binary, and `source_sha256` and `binary_sha256` enter the TCB and the fingerprint. A compilation failure → `inspector_build_failed` (exit 2).
- **How it is tested.** `tests/stage_b`: the inspector's identity depends on the toolchain; the report's `source_sha256` is the hash of the source; the version declared in Lean and in Python match. Additional evidence: the output of the compiled executable is **byte-for-byte identical** to the interpreter's (`lean --run`) on fixture 05.

### D-8. Reported declarations
- **What it does.** The report covers the constants of the target module that (a) have a declaration range in the source (`declRangeExt`) and (b) have a user name. Private names are judged by their user part. Left out: `match_N`, `_proof_N`, recursors, `noConfusion`, equations.
- **What changes in behaviour.** Generated constants with a range in the source are also included: a `structure`'s constructor and projections, anonymous instances (`instInhabitedP`) and the parser created by `macro` (`tacticObviously`). Each gets its own states. `private` declarations are reported with their internal name (`_private.Mod.0.hidden`); the link to Stage A (`set_option … in`) uses the user name.
- **How it is tested.** `tests/stage_b::test_reported_declarations_exact` (the exact set per fixture, including `edges` and `macro`); `test_edges_internal_names_never_reported`; `test_edges_private_declaration_reported_and_owned`. Mutations: removing the range filter and the handling of private names are detected.

### D-9. Toolchain format
- **What it does.** To check that the inspector ran with the pinned Lean, the wrapper extracts the version from `leanprover/lean4:vX.Y.Z` (with an optional `-rcN`) and compares it with the `Lean.versionString` emitted by the inspector.
- **What changes in behaviour.** Toolchains in another format (`nightly-…`, forks, `stable`) → `toolchain_unrecognized`, exit 2, without trying to audit. A version mismatch → `toolchain_mismatch`, exit 2.
- **How it is tested.** `tests/stage_b::test_unrecognized_toolchain_format` and `test_ingest_file_level_mismatch`. The mutation that removes the version check is detected.

### D-10. Line endings
- **What it does.** `.gitattributes` with `* -text` turns off git's automatic line-ending conversion. The generators write UTF-8 bytes with LF, and `--check` compares bytes, not text.
- **What changes in behaviour.** On Windows, without this, the checkout would convert `lake-manifest.json` to CRLF: `env_pin` would change and every project allow-list would look stale. The TCB hashes (inspector source, policy) would also change between systems.
- **How it is tested.** Indirectly: `tests/maintenance/test_allowlist_fresh.py` compares bytes and passed on both systems (Linux and Windows), and the pin tests depend on the exact bytes.

## Local decisions on the Policy, Schema and CLI (for veto)

- **D-11. `debug.skipKernelTC true` is a forbidden `set_option`.** The option makes Lean accept declarations **without** kernel checking; it is the extreme case of "a set_option that relaxes checking". Test: `tests/policy/test_rules.py::test_forbidden_option_rejects`.
- **D-12. Options allow-list.** Recognized: `maxHeartbeats`, `maxRecDepth`, `synthInstance.maxHeartbeats`, `synthInstance.maxSize`, `autoImplicit`, `relaxedAutoImplicit`, `checkBinderAnnotations`, and the prefixes `linter.`, `pp.`, `trace.`, plus `profiler`. An option outside the list → `Não resolvida`, `set_option_unrecognized`. Mathlib probably uses options outside it; the list will be adjusted with layer-2 evidence.
- **D-13. Reach of `set_option` at file or section level.** It hits every declaration that is not provably **before** the option. The end of a section is not tracked (a conservative approximation: more declarations hit, never fewer). An `in` form that does not bind to a named declaration, with the option forbidden or unrecognized → `set_option_unattributed` on every declaration. End-to-end test: `tests/policy/set-option`.
- **D-14. A declaration seen by Stage A and missing from the environment** → its own entry in the report, `Não resolvida`/`Não resolvido`, reason `declaration_not_found_in_environment`, exit 1.
- **D-15 (REVISED by the reviewer: exit 2, `no_declarations_found`, `--allow-empty`; original text:)** A file without declarations → `no_declarations`, exit 1 (nothing to seal, never exit 0). The schema requires exit 0 to have at least one declaration.
- **D-16. Input not recognized by Stage A** (new syntax, a command outside the allow-list, forbidden Unicode) affects only `proof_status` (`Não resolvida`, `stage_a_unrecognized`). The premises come from the elaborated environment, which Stage B analysed completely.
- **D-17. Precedence within each state:** the worst effect wins (`Rejeitada` > `Não resolvida` > `Validada`; `Não conforme` > `Não resolvido` > `Conforme`). It is the same rule as Q4, applied within each state: `sorry` + an `implemented_by` candidate → `Rejeitada`.
- **D-18. `declaration_hash`** = SHA-256 of (name, declaration kind, `Expr.hash` of the type, `Expr.hash` of the value). Deterministic; the underlying `Expr.hash` is a 64-bit structural hash (L-14). It is `null` for a non-elaborated declaration.
- **D-19. Report layout.** The spec lists `tcb` and `execution_metadata` as per-declaration fields; they are in each declaration (a copy) **and** at the report level. There are also file fields (`compilation`, `infrastructure`, `file_findings`, `not_covered`, `exit_code`). The schema ties `overall_status` to the Q4 table, `correspondence_status` to the constant `Não auditada`, `Validada` to a complete TCB, and exit 0 to the absence of unrecognized entries.
- **D-20. Dependency `jsonschema` (≥ 4.18)** at run time. The CLI validates every report before writing it; a report outside the schema → `report_schema_invalid`, exit 2.
- **D-21. Default timeout of 300 s** (the spec's 5-min budget), configurable with `--timeout`; `--timeout-test artificial` marks the report (L-11). **Revised in instruction 11:** 90 s per file (`--timeout-file`).

## Instruction 10 round — resolutions

- **Q8 — RESOLVED** with the reviewer's criterion: fail-closed if the command *can execute compiled code at elaboration time, before Stage B can inspect the environment*. `#guard_expr`, `#check_tactic` → fail-closed; `#check`, `#synth`, `#check_simp` → allowed (reviewed). The criterion and the table are in `limitations.md` (L-17); `classification_version = "3"`.
- **D-15 — REVISED** as per the reviewer: a file without declarations → exit 2, `no_declarations_found`. `--allow-empty` makes the import-only file case explicit (exit 0, warning `empty_file_allowed`, `execution_metadata.allow_empty: true`). The schema requires that exit 0 without declarations has `allow_empty: true`.
- **Accepted:** D-4 to D-13 and D-20.
  - D-7: the cache hit rate is measured in the Action (`docs/ci.md`).
  - D-8: the exclusions are in L-15.
  - D-20: `jsonschema` and its transitive closure enter the TCB (`tcb.aggregator.python_dependencies`, with exact versions); an unresolvable dependency → incomplete TCB.
- **Transitive anti-LLM test:** it walks the same closure as the TCB (`src/auditor/pydeps.py`); a new dependency, even a transitive one, that brings in an LLM library makes it fail (tested with a two-level synthetic graph).
- **Versioned mutation tests:** `tools/mutation/` + `docs/maintenance.md`, with a catalog-integrity test.

## Local CI decisions (for veto)

- **D-22. Job failure.** A file with exit 1 (rejection or non-resolution) makes the job fail; only infrastructure (budget, timeout, exit 2) leaves the job green with the `auditor-failed-infra` label. Whether the job's check blocks merging is a setting of the target repository (branch protection), not of the tool.
- **D-23. `auditor-tier1.yml` is reusable** (`workflow_call`), with call templates in `ci/templates/`. In this repository it does not run on `pull_request`: the fixtures are rejected on purpose, and auditing them here would only produce meaningless red jobs. The auditor's own CI is `ci.yml` (the whole suite).
- **D-24. Privilege separation into three workflows.** The job that runs PR code has read-only access. The label comes from `workflow_run` (no checkout, artifact treated as untrusted). The comment comes from `issue_comment` (no checkout, only OWNER/MEMBER/COLLABORATOR). Rejected alternative: `pull_request_target` with a checkout of the PR, which would give a write token to untrusted code. Tested as policy in `tests/ci/test_workflows.py`.
- **D-25. Version pinning** (**revised in instruction 11**: SHA mandatory; see D-35). The elan installer pinned to `v4.2.4`. Official GitHub actions pinned by major version tag (`@v4`, `@v5`), not by SHA; the test accepts both formats. For the fork, I recommend pinning by SHA (a change only in the templates).
- **D-26. `#check_tactic_failure`** was classified as fail-closed by direct derivation from the Q8 criterion (it runs a user tactic, like `#check_tactic`).
- **D-27. `auditor-ci` subprocess.** Each file is audited in a separate process (`python -m auditor check`), with the same package that orchestrates (the package path on `PYTHONPATH`). The isolation keeps one file from affecting the next; the subprocess timeout is the remaining budget + 30 s.
- **D-28. What the 5-min budget measures** (**revised in instruction 11**: it includes preparation). The budget covers the audit (all files, including the `lake build` of each target module). Installing elan and Python and `lake exe cache get` are outside it: they are runner preparation, measured by the job's total duration. If the reviewer understands that the spec's 5 min include preparation, the adjustment is to pass the time already spent in the job to `auditor-ci` to deduct from the budget.

## Instruction 11 round — resolutions

- **Accepted without modification:** D-14, D-16, D-17, D-19, D-20, D-22, D-23, D-24, D-26, D-27.
- **D-18 — ACCEPTED for Phase 0**, with L-14. A Phase 1 item in `docs/roadmap.md`: replace the 64-bit structural hash with SHA-256 truncated to 128 bits or BLAKE3-128 (64 bits does not resist adversarial collisions: whoever forges a collision swaps a declaration without changing the hash).
- **D-21 — REVISED:** a **per-file** timeout of 90 s (`--timeout-file`, in the CLI and in `auditor-ci`); the 5-min budget is the PR's wall clock; a file that exceeds the timeout ends the PR's audit with exit 2. The default will be readjusted by the p95 measured in layer 2 (`tools/layer2/timings.py`).
- **D-25 — REVISED, mandatory:** every action pinned by commit SHA, in this repository and in the templates; update procedure in `docs/maintenance.md`. Applying it exposed an error in the original D-25 (D-35).
- **D-28 — REVISED:** the budget is the PR's wall clock, from the trigger to the report, **including `lake exe cache get`**. 5 min is the steady-state SLA; a `cold` cache → extended budget (15 min), `first_run: true`, `cache_cold_extension` and the `auditor-first-run` label when it goes past 5 min. The layer-2 measurement PRs are made after the first run.
- **README, "Status":** "Phase 0 = Layer 1 (done) + Layer 2 (pending user evidence)"; Phase 1 depends on layer 2.

## Local decisions of instruction 11 (for veto)

- **D-29. PR exit 2 and job colour.** `auditor-ci run` exits with the PR's exit code (0/1/2). Infrastructure wins: rejection + timeout → exit 2. The job colour remains that of D-22: the audit step accepts 0/1/2, and a dedicated step fails the job only when `audit_failed` is true. Exit 2 alone → green job + `auditor-failed-infra` (spec criterion 3: does not block merging).
- **D-30. Clock origin.** First attempt: `github.event.pull_request.updated_at` (the PR event; includes the runner queue). Re-run (`run_attempt > 1`): the start of the job, otherwise a re-run would be born with its budget exhausted. `outcome.json` declares `clock_origin` (`trigger`, `job_start`, or `auditor_start`/`auditor_start_fallback` outside GitHub or with an invalid timestamp).
- **D-31. How `cache_state` is measured.** Two signals: restoration of the target's build cache (`hit`/`partial`/`miss`/`none`) and the presence of the inspector binary. `cold` = some cold signal; `delta` = partial build cache; `warm` = the rest. The extended budget is only granted with positive evidence of a cold cache. `first_run` is `cache_state == cold`: it includes an evicted cache (GitHub removes caches unused for 7 days), not only the literal first run in the fork.
- **D-32. Mathlib cache in the job.** `~/.cache/mathlib` (where `lake exe cache get` keeps its files) is restored with `actions/cache/restore`, keyed by OS + `lean-toolchain` + base commit, `restore-keys` by prefix (`partial`), and saved when there was no exact hit. The size of this directory against the repository's cache limit is a layer-2 check.
- **D-33. Labels.** `auditor-failed-infra` wins over `auditor-first-run`: a cold cache that exceeds the extended budget is infrastructure. `auditor-first-run` only when `cache_cold_extension` (cold, no infrastructure, total > 5 min). The label workflow accepts only these two names.
- **D-34. Inspector compiled before the first file.** With the binary out of cache, `auditor-ci` compiles it before auditing: the cost goes into the PR budget, not into one file's 90 s timeout.
- **D-35. Correction of the original D-25: elan was not pinned.** The `elan-init.sh` taken from tag `v4.2.4` downloads elan's **`latest`** release (`releases/latest/download/...`). The previous report said "elan pinned at v4.2.4", which was only true for the script. The workflows now download `elan-x86_64-unknown-linux-gnu.tar.gz` from release `v4.2.4` and check the SHA-256 before running it. Residue (L-18): the Lean toolchain downloaded by elan and the Python dependencies installed by pip are not hash-checked in CI.
- **D-36. `--timeout` is still accepted** as a synonym of `--timeout-file` in the CLI (same destination; the default is 90 s). **Rejected in instruction 12** (see there).
- **D-37. `outcome.json` became `auditor-ci-outcome/2`.** `label-decision` rejects the previous version (resulting in `auditor-failed-infra`, fail-closed).
- **D-38. Fanout for choosing the measurement file.** `tools/layer2/fanout.py`: fanout = the number of project modules that import the module, directly or transitively, from the import header. An unreadable import name (e.g. with `«»`) is an error, not ignored.

## Instruction 12 round — resolutions

- **Accepted:** D-29, D-30, D-31, D-32, D-33, D-34, D-35, D-37.
- **L-18 → roadmap (Phase 1):** Lean toolchain and Python dependencies verified by hash (`docs/roadmap.md`).
- **D-36 — REJECTED and applied:** `auditor check --timeout` was removed (no synonym). The "total" names went to the PR budget in `auditor-ci`: `--budget` → `--timeout-total`, `--first-run-budget` → `--timeout-total-first-run`; workflow inputs `budget-seconds` → `timeout-total-seconds`, `first-run-budget-seconds` → `timeout-total-first-run-seconds`. The per-file timeout remains `--timeout-file` (D-21 accepted). Recorded in `CHANGELOG.md`. **Interpretation to be confirmed:** the instruction says "rename `--timeout` to `--timeout-total`". In the `auditor check` CLI, which audits one file, `--timeout` was the per-file timeout, already called `--timeout-file`. Renaming it to `--timeout-total` would undo D-21. That is why the "total" name was applied to what is actually total: the PR budget. If the intention was different, the change is mechanical.
- **D-38 — details:** `docs/ci.md`, "Choosing the highest-fanout file (D-38)": (a) algorithm, (b) justification and alternatives, (c) tests. Run on the real Mathlib (commit `e1b2403b`, 8651 modules, no header error). The forward closure (`imports_transitive`) was added, because the cost of auditing a file grows with it, not with fanout.
- **Layer-2 blocker — option (X) executed:** the auditor's toolchain `v4.22.0` → **`v4.36.0-rc1`** (Mathlib `master`'s, commit `e1b2403b`, on 2026-10-20). Allow-list regenerated, inspector ported, fixtures recompiled, whole suite run. Procedure in `docs/maintenance.md`, "Procedure when bumping the toolchain". Two findings change meaning (D-39, D-43) and one changes the boundary (D-42).
- **Execute or prepare — prepare:** `docs/layer2-checklist.md`. Nothing public was executed.
- **Requested confirmations:**
  - (a) `docs/invalidation.md` exists (versioned since commit `09a8550`);
  - (b) D-18 is in `docs/roadmap.md` (row "Collision-resistant declaration hash"), together with the new L-18 item;
  - (c) Mathlib `master` uses `leanprover/lean4:v4.36.0-rc1` (Lean commit `c9afcddf`), read from the `lean-toolchain` of commit `e1b2403bdd31a2756e30282d62b3fa54cc95c869` on 2026-10-20.

## Q9. `native_decide` on v4.36 — DECIDED in instruction 13: option (a)

**What changed.** On v4.22, `native_decide` produced a term with `Lean.ofReduceBool`, a fixed, known axiom; the policy treated it as native evaluation with a justification (O-1). On v4.36.0-rc1 (`Lean.Meta.nativeEqTrue`), the tactic compiles and evaluates `e`, and then **adds a new axiom to the environment, per use**: `<owner>._native.native_decide.ax_N : e = true` (the same holds for `bv_decide`). The kernel never re-checks this axiom.

**The problem.** The environment does not record that the axiom came from the tactic. A hand-written `axiom` with the same name and type is indistinguishable (demonstrated: fixture `edges`, `uses_spoof`, locked by a test). An imported tactic (another file of the PR, or a dependency) can also add an axiom of this shape without the target file's Stage A seeing anything.

**Current behaviour (D-43), fail-closed.** The inspector recognizes the shape (`native_auxiliary`). The policy applies the justification and combined-pattern rules as before, and **additionally** leaves the premises `Não resolvido` (`native_auxiliary_axiom`). Effect on conformance: only the justified cases changed, from `verified` to `unresolved` (`nd_justified`, `consumes_justified`, `add_native`); `f_bad`/`e_bad`/`e_mixed` remain `Rejeitada`, with premises `Não resolvido` instead of `Conforme`. No rejection was lost.

**Options:**
- **(a) Permanently fail-closed in Phase 0** (the current behaviour): `native_decide` never comes out `verified`. The O-1 justification remains mandatory (without it, `Não conforme`), but it is not enough. Simple and correct. Cost: whoever uses `native_decide` with a justification loses `verified`. Mathlib already forbids `native_decide` by its own policy, so the impact on the main target is small.
- **(b) Corroboration.** Accept the auxiliary axiom as native evaluation (and, with a valid justification, `verified`) only if: the shape matches; the owner is in the audited file; Stage A saw `native_decide`/`bv_decide` inside the owning declaration; there is no `axiom` with that name in the file; there is no fail-closed command in the file. **Not sound against an adversary:** `first | native_decide | malicious_imported_tactic` satisfies all of it, with the axiom forged by the imported tactic.
- **(c) Re-evaluation by the auditor.** The auditor compiles and evaluates `e` again, in a separate process. This brings back executing PR code in the auditor (against D-39) and gives the same trust in the compiler as `native_decide`. Heavy.
- **(d) Re-checking by the kernel.** The inspector tries to reduce `e` to `true` with the kernel (`Kernel.whnf`), with an effort limit. If it succeeds, the axiom is admissible without trusting the compiler: `verified` without native evaluation. If it does not succeed within the limit, `Não resolvido`. It is sound. But `native_decide` exists precisely where the kernel is slow, so in most cases the result would be `Não resolvido`, as in (a), at a CPU cost.

**Recommendation: (a) in Phase 0, and (d) as an item to evaluate in Phase 1.** (b) gives an appearance of verification that an adversary bypasses. (c) contradicts D-39.

## Local decisions of instruction 12 (for veto)

- **D-39. The inspector does not run code from the imported environment.** On v4.36, `importModules (loadExts := true)` requires `enableInitializersExecution`, which would run the imported modules' `initialize` blocks — including the PR's — inside the inspector. The inspector now imports with `loadExts := false` and reads each extension through the modules' entries. Consequences:
  - the official `collectAxioms`, without the precomputed-axioms extension, walks the bodies (L-20);
  - a Verso docstring (without raw text) counts as a missing justification;
  - the fingerprint's `@[simp]`/`@[ext]` come from the recorded global entries, not from the final state; a global `attribute [-simp]` is not discounted (the fingerprint changes definition; the inspector went up to version 4).

  Only the allow-list generator runs initializers, during maintenance, on reviewed code.
- **D-40. Classification of the 40 new v4.36 commands** (`classification_version = "4"`):
  - `allowed` (11): `#check_assertions`, `#import_path`, `#show_deprecated_modules`, `assert_not_exists`, `assert_not_imported`, `deprecated_module`, `deprecated_syntax`, `grind_annotated`, `coinductive` (a declaration; it also joined Stage A's declaration keywords), `recall`, `unlock_limits` (D-41);
  - `metaprogramming`/fail-closed (29): `#guard_panic`, `#grind_lint`, `reprove` (runs a tactic with no inspectable result, like `#check_tactic`), `with_weak_namespace` (the wrapped command is indented and would escape the column-0 check), `docs_to_verso`, the `cbv_simproc` family (6), the `declare_*config_elab*` and `def_eval_config_item` (5), the `declare_decidable_*`/`declare_eval_bin*` (5), the `register_*` (6) and `set_library_suggestions` (evaluates a term as a suggestions engine; replaces `set_premise_selector`, which was fail-closed).

  Removed: `set_premise_selector`.
- **D-41. `unlock_limits`** (sets `maxRecDepth`, `maxHeartbeats` and `synthInstance.maxHeartbeats` to zero) is recorded by Stage A as the three `set_option … 0`, with `via: "unlock_limits"`, including in the `unlock_limits in` form. The existing policy decides: `maxHeartbeats 0` → `Rejeitada`. Tested end to end (fixture `set-option`, `unlocked`).
- **D-42. The toolchain's roots changed:** v4.36.0-rc1 also declares `LeanChecker`, `LeanExport` and `LeanIR` (all from the Lean distribution). By the Q7-a rule (a root declared by the toolchain = TCB), they enter automatically. By `docs/tcb.md` (ii), this requires review by someone other than the author: **requested here**.
- **D-43. Native auxiliary axiom: provisionally fail-closed.** The inspector emits `native_auxiliary` (shape: name `…._native.<tactic>.ax_…` and type `@Eq.{1} Bool e Bool.true`, `e` closed). The policy has `axioms.native_auxiliary_action`, whose only option is `"fail_closed"`; the schema gained the `native_auxiliary` classification. It stays this way until Q9.
- **D-44. One supported toolchain at a time.** The v4.22.0 core allow-list was removed: without a matching inspector and suite, it would be an unverified promise.
- **D-45. A dedicated CI fixture** (`tests/ci/clean-project`): the `auditor-ci` tests used scenario 06 as "a project that passes entirely". With Q9, it stopped passing; the new fixture separates the CI tests from the policy decision.
- **D-46. The owner convention for `where` auxiliaries changed** (L-4): the auxiliary axiom of `outer.aux` is referenced by `outer.aux` itself, which becomes the owner (before, `outer`). The justification is now looked for where the `native_decide` is written. Locked by a test.

## Instruction 13 round — resolutions

- **Q9 → (a), permanent in Phase 0.** `native_decide` (and every native evaluation through `nativeEqTrue`) never comes out `verified`. Reason recorded by the reviewer: certifying it would depend on internal compiler details that change between versions, and Phase 0 is designed to be stable across toolchain bumps. (b), (c) and (d) were rejected, each for the reason given in the question. Option (d) went onto the Phase 1 roadmap as a **research** item, with a criterion of ≥ 50 % of justified cases and keeping D-39. If it does not meet the criterion, it stays fail-closed forever. Code: no change (it was already D-43's behaviour). Documentation: `docs/limitations.md` (L-19), `docs/tcb.md`, `docs/roadmap.md`, `CHANGELOG.md`.
- **D-36: interpretation confirmed.** `--timeout-total-first-run` is documented as the **extended** budget of a run with a cold cache, not as a second permanent budget, in `CHANGELOG.md` and in `docs/maintenance.md` ("CI time budgets"). The 5-min SLA is a steady-state one.
- **D-42: approved on condition, condition applied.** See D-47.
- **Accepted without modification:** D-39, D-40, D-41, D-43, D-44, D-45, D-46.
- **Mutation in batches:** `stage_b` → `policy` → `ci`, one group at a time, with a commit between groups. **115/115 detected in the 5 groups, 0 survivors.** There was 1 real survivor in Stage B, fixed with a new test. Details in `docs/maintenance.md`, "Run log".
- **D-38, reproducibility:** `fanout.py` does not access the network or `master`. It records provenance (commit, SHA-256 of `lake-manifest.json`, `lean-toolchain`) and accepts `--expect-commit`, which exits with 2 if the checkout is not the pinned one. **Correction of a premise:** there is no D-38 drift test against the real Mathlib in the suite, because the suite does not download Mathlib. The guarantee is the provenance checked during the measurement (checklist, step 6). The mechanism is tested in `tests/maintenance/test_layer2_tools.py`.
- **`Mathlib/Logic/Basic.lean` → `Mathlib/Basic/Logic/Basic.lean`:** recorded in `CHANGELOG.md`. A search of the repository (`git grep`): no script, fixture or test uses the old path. Only `docs/ci.md` and the checklist cited it, and both were updated.
- **Share of `native_decide` in Mathlib (measured now, at the pinned commit):** `tools/layer2/native_usage.py` (Stage A's lexer and rule; comments and strings do not count):
  - `Mathlib` library: **2 of 256,505 declarations with a body** (0.0008 %). Both are **metaprogramming code**, not proofs: the `+native`/`native := true` syntax patterns of the linter that **forbids** native evaluation in Mathlib, and a configuration field of the `inclusion` tactic. **Library proofs that use native evaluation: 0.**
  - `MathlibTest` (outside the library): 33 of 7,463 declarations; the largest concentration is in `MathlibTest/Algebra` (17 of 34).
  - Conclusion: the impact of Q9 on the main target is nil today. The 3 layer-2 reports include the measurement, over the whole of Mathlib and per PR (checklist, steps 6 and 10).
- **Related finding:** Mathlib's `inclusion` tactic (`Mathlib/Tactic/Inclusion/Core/Core.lean`) calls `nativeEqTrue` directly when used with `+native`. It is exactly the case of "an imported tactic that creates the auxiliary axiom" from Q9 (b). The generated axiom (`…._native.inclusion.ax_…`) has the shape recognized by the inspector and comes out `Não resolvido`, like `native_decide`. This confirms that option (b) would be bypassable without any adversary: a legitimate tactic with another name suffices.

## Local decisions of instruction 13 (for veto)

- **D-47. D-42's condition applied to every root, including v4.22's.** The reviewer's principle ("the roots that the target project actually uses") holds for every declared root, not only for the three new ones. Measured on the import closure of the `Mathlib` library (`e1b2403b`, 10,527 modules, with the 8 dependencies checked against the `rev` in `lake-manifest.json`), the roots used are `Init` (668 modules), `Lake` (1: `Lake.Util.Casing`, via `public meta import` in `Mathlib.Tactic.Linter.TextBased`), `Lean` (741) and `Std` (215). Left out: `LeanChecker`, `LeanExport` and `LeanIR` (the three new ones) and **also `LakeMain` and `Leanc`**, which had been TCB since Q7-a. The change goes in the fail-closed direction: an `@[extern]`/`@[implemented_by]` from these roots now comes out `unresolved` (`module_root_not_used_by_target_project`). If the intention was to restrict only the three new ones, it is enough to add `LakeMain` and `Leanc` to the allow-list.
  - **Note on "check against `lake-manifest.json`".** The manifest does not list toolchain roots, only packages. The check implemented is the closest to what the condition asks: the closure is computed with each dependency at exactly the revision the manifest pins (the generator refuses a package off its `rev`), and the manifest's SHA-256 is recorded in the allow-list.
- **D-48. A roots allow-list per toolchain, checked at run time.** The file is `src/auditor/data/tcb_roots/<toolchain>.json`, generated by `tools/gen_tcb_roots.py`. The boundary now requires this file. A toolchain without a file, a file from another toolchain, declared roots different from the recorded ones (toolchain drift) or a root of the allow-list that is not declared → `tcb_boundary_undeclared` (exit 2).
- **D-49. D-42 drift at two levels.** (i) Scenario `06-tcb-boundary` gained one declaration per root of the allow-list (`uses_init`, `uses_lean`, `uses_std`, `uses_lake`, each using an `@[extern]`/`@[implemented_by]` constant from that root), which must come out TCB; if the allow-list stops recognizing the root, the scenario fails. (ii) A unit test with a synthetic toolchain covers a declared but unused root (→ `unresolved`) and drift of the declared list. The check against the real Mathlib stays in the layer-2 checklist (step 3, `gen_tcb_roots.py --check`), because the suite does not download Mathlib.
- **D-50. `import all` in the header parser.** `fanout.py` (and the roots generator, which reuses it) now treats `all` after `import` as a modifier. Before, `all` was read as a module name. This did not change the fanout ranking (the name was dropped as external), but it would make the roots closure fail with "import without a source".
- **D-51. The native-evaluation measurement is lexical and declared as an estimate.** It reuses Stage A's rule and also counts `bv_decide`, which Stage A does not list. That is not a hole: the verdict comes from Stage B, by the axiom's shape. The per-declaration verdict remains the auditor's (`native_auxiliary_axiom`), which also catches tactics such as `inclusion +native`.

## Instruction 14 round — resolutions (layer 1 closed)

- **Layer 1: accepted as closed.** 558 tests; 115/115 mutations in the 5 groups, 0 survivors and 0 skipped.
- **Q9-a: confirmed by the measurement.** The measurement was recorded in `docs/tcb.md` (decision Q7-a) and on the Phase 1 roadmap, next to (d) and the ≥ 50 % criterion.
- **D-47: accepted, with four mandatory additions, all made:**
  1. **Renamed:** `tcb_roots` → `target_trusted_roots`. This applies to the directory `src/auditor/data/target_trusted_roots/`, to `load_target_trusted_roots` and to the field `Boundary.trusted_roots`. In the Stage B result, `boundary.toolchain_roots` became `boundary.trusted_roots`, next to `boundary.declared_roots`. The JSON gained the `meaning` field, which says what it means and what it does not mean. The generator's name (`tools/gen_tcb_roots.py`) stayed as it was, because it is the one cited in the instruction's text.
  2. **L-21** in `docs/limitations.md` (Phase 0 is Mathlib-oriented; other targets generate their own file; false positives may appear).
  3. **Phase 1 roadmap:** automatic root discovery for arbitrary targets, with the same verification policy against `lake-manifest.json`.
  4. **`docs/tcb.md`:** a table with the roots declared by Lean v4.36, those used by Mathlib `e1b2403b` and those in `target_trusted_roots`.
- **D-48, D-49, D-50: accepted.** **D-51: accepted with a note.** The exact count, by compilation, was recorded as a Phase 1 item on the roadmap.
- **D-38: accepted.** Recorded as **L-22** in `docs/limitations.md`.
- **`rea` (MCP) and the suite:** no test depends on an MCP server. `git grep` in `tests/`, `src/`, `tools/` and `pyproject.toml` finds no reference, and the whole layer-1 suite (558) ran **after** WSL was shut down, with `rea` disconnected.
- **Layer-2 preparation:**
  1. **Abort criteria for a failure that is not infrastructure.** The existing ones covered the environment signals (step 5) and `unknown_command`, `inspector_disagreement` and `missing_constants` (step 7). They did **not** cover:
     - the probe lemma not coming out `verified`;
     - a declaration the PR did not touch coming out `Rejeitada`, `Não conforme` or `Não resolvido`;
     - `native_auxiliary_axiom` in the library;
     - `tcb_boundary_*`;
     - a diverging `--check` midway through the measurement.

     The checklist gained the section "A failure that is not infrastructure", which applies to every step: stop, do not adjust anything to make it pass, do not repeat, bring the artifacts. The classification happens outside the run.
  2. **Smoke test (step 3b, before any PR).** It runs `auditor-ci run` on a single file (`Mathlib/Logic/Hydra.lean`) at the pinned commit, with `--build-cache miss`, and checks `cache_state: cold`, `first_run: true`, `infra_failed: false`, `exit_code` 0, no `allowlist_unavailable` or other environment signal, and every declaration `verified`. The commands were run here on the `tests/ci/clean-project` fixture, with the same CLI and the same checks: `cold`, `first_run: True`, `exit_code` 0, no environment signal.
- **Observed flakiness (no known cause).** After the rename, `test_06_toolchain_extern_does_not_trigger` failed once, in a run combined with other files whose output was not saved. It then passed 4 times: 3 alone and 1 in the same combination. The cause is not known, and none is claimed here. From now on, runs in parts keep the log of any failure. If it happens again, there will be evidence.

## Instruction 15 round — layer 2, first `auditor-prep`

The first `auditor-prep` in the fork (`Enzo47961/mathlib4`, `auditor-base` = `847592d` on top of `e1b2403b`; run 39656457392) stopped at step 3. The fail-closed behaviour in the smoke test was the expected one: without an allow-list, 0 `verified` and 20 `unresolved` (`stage_a_unrecognized`). The three failures below are real tool bugs, found by the target environment and undetectable in layer 1 (L-23).

- **D-52: approved.** The generator extracts only from the `@[default_target]` `lean_lib`s (or `--lib`).
  - **Cause:** `project_modules()` imported every `.olean` of the build, including Mathlib's `Cache` library, which defines `Lean.Name.fromComponents` as `Mathlib.Lean.Name`. D-6 assumed a project with a single library.
  - **Tests:**
    - (a) `test_extraction_ignores_non_target_library`: the mini-project gains a second `lean_lib` (`Tool`) that defines the same name as `Mini`. The default extraction uses only `Mini`, and asking for both (`--lib Mini --lib Tool`) fails with exit 2, which proves the fixture's collision is real.
    - Reading of `.lean` and `.toml` lakefiles; a lakefile without `@[default_target]` → an error asking for `--lib`.
    - (b) Mutations in the `allowlist` group: going back to listing everything; accepting `defaultTargets` that are not `lean_lib`s; accepting a lakefile without a target.
    - (c) The real case (Mathlib + `Cache`) is checked by the next `auditor-prep`.
- **D-53: approved, strong option (normalize, not just document).** CRLF → LF before hashing in `env_pin` and in `gen_tcb_roots.py`, and also in `fanout.py`'s provenance, so that the three hashes of the same manifest match. SHA-256 of the normalized content (not git's blob, which is SHA-1; D-18).
  - **Versions:** `ENV_PIN_VERSION` `2`; `generator_version` `3`.
  - **Regeneration:** `target_trusted_roots` was regenerated in the local clone (Windows, CRLF) of `e1b2403b`. Only the hash changed, to `f77f47db…`, the same one the Linux runner computed: direct evidence that the normalization works across systems.
  - **Tests:**
    - `test_env_pin_ignores_crlf`;
    - `test_allowlist_survives_line_ending_change` (generated with LF, used with CRLF, and the reverse; Stage A and `--check`);
    - `test_gen_tcb_roots_manifest_hash_ignores_crlf` (generator and `fanout`);
    - the versioned file locked at `f77f47db…`.
  - **Mutations:** one in each place.
  - **Note on D-10:** `.gitattributes` (`* -text`) protects only the auditor's repository, not the target project, which is cloned with the cloner's configuration. Normalization is the guarantee; D-10 still holds for the auditor's own files.
- **D-54: approved as proposed, with the invariant made explicit.** `--check` accepts `HEAD` ≠ recorded commit only if the recorded one is an ancestor, the working tree (not only `HEAD`) differs only in `.github/` and no `.lean` file changed, not even inside `.github/`. Recorded as **L-24**: a relaxation specific to the measurement in a fork; in the real repository the strict check applies.
  - **Tests:**
    - accepted: only `.github/`;
    - rejected (5): `README.md`, a `.lean` file with the same closure, `.github/Gen.lean`, an uncommitted change, a sibling commit (not an ancestor, but differing only in `.github/`);
    - the strict check when `HEAD` = recorded commit.
  - **Mutations:** a new `gen_tcb_roots` group (8).
  - **Real run:** in the fork's local clone (`847592d`), `--check` passed through the fork path.
- **D-55: approved.** `runs-on: ubuntu-24.04` in the reusable workflow, in `ci.yml`, in the templates and in the fork's `auditor-prep`. Updating the Node 20 actions is left for a separate round, outside layer 2, recorded in the CHANGELOG.
- **`syntax_extension_declared` with `command: "?"`:** to be checked in the next smoke test. If it persists with the Mathlib allow-list present, it is a failure that is not infrastructure and will be treated as a bug; if it disappears, it is recorded as a consequence of the missing allow-list.
- **Record requested as "L-19":** the number L-19 already exists (native-evaluation auxiliary axiom, Q9). The text was recorded as **L-23**, and the D-54 relaxation as **L-24**.
- **Revalidation:** only the touched mutation groups (`allowlist` and the new `gen_tcb_roots`) were re-run. `policy`, `ci`, `stage_a` and `stage_b` remain validated by the earlier commits, because their code did not change. The full suite was re-run.

## Instruction 16 round — second `auditor-prep`

The second `auditor-prep` (run 39666288403, auditor `c3dcf08`) confirmed D-52 to D-54 on the real Mathlib: an allow-list with `libraries: ["Mathlib"]`, 8651 modules and 259 commands; `--check` accepted through the fork path. The smoke test (`Hydra.lean`) still came out 20/20 `Não resolvida`, for three reasons. The first was expected; the other two are layer-1 bugs that no fixture exercised (L-23).

- **Classification of 98 Mathlib commands:** a human decision. A draft authorized, with a justification per command by the L-17 criterion; review by a second human; commit in the fork only afterwards. An ambiguous command → fail-closed, recorded in `limitations.md`.
- **D-56: approved.** `?` is in `syntax_extension` in the core (`classification.toml`), and Stage A looked for it in any position, like the reserved words. Every `?_` became `syntax_extension_declared`: at the pinned commit, 4748 of Mathlib's 8650 files contain `?_` or `?name`.
  - **Fix:** reserved words (identifiers, `#commands`) are still looked for in any position; symbol commands (`?`, `$`) only at the start of a command.
  - **Tests:**
    - (a) `?_`, `?m`, `?x.y` and `f $ x` inside terms produce nothing;
    - (b) `?` and `$` at column 0 remain `syntax_extension_declared`;
    - (c) an indented `macro` and one in the middle of the line are still detected.
  - **Detail:** the allow-list stores `«$»` normalized as `$`, which is the token the lexer produces.
- **D-57: approved.** `module` is only accepted as the file's first token (comments do not become tokens).
  - **Tests:** accepted with `public import`, `import` and a module docstring; accepted alone; `unknown_command` after `import`, after a command, duplicated, and after a docstring.
  - **Conformance fixture `07-module-header`** (Stage A → Stage B → policy):
    - `module` + `public import Fixture.Base` (also a `module`) + `refine ⟨?_, ?_⟩` → `both` `Validada`/`Conforme`/`verified`;
    - a control with `sorry` → `Rejeitada`;
    - ground truth by `#print axioms`.
- **Versions and mutations for D-56/D-57:** `stage_a_version` `2`. `stage_a` group: 4 new mutations (accept `module` in any position; never accept it; symbols in any position; symbols never), 13/13 detected.
- **D-58: approved.**
  - (a) The two timeout tests use a fixture that compiles in seconds and check `duration_s ≥ 1`.
  - (b) `test_all_pass` warms the inspector cache first.
  - (c) The `ci.yml` suite (Linux) is the layer-1 reference.

## Instruction 17 round — draft of the Mathlib classification

The draft classification of Mathlib's 98 commands (outside this repository: the fork's `.auditor/classification.toml`, not yet committed) was approved by the reviewer as the basis for the human review. Result: 63 `allowed`, 32 `metaprogramming`, 3 `syntax_extension`; 9 ambiguous, fail-closed as a precaution (except `#string_diagram`, allowed as a precaution).

- **Divergences from the reviewer's prior list: they are corrections, not disagreements.** The prior list was made from the commands' names; the draft, by reading each one's implementation at the pinned commit. The reading prevailed in the 7 cases: `#count_heartbeats`, `#leansearch`, `#loogle`, `#search`, `#parse`, `deprecate` (allowed → fail-closed) and `notation3` (allowed → `syntax_extension`). In their answer, the reviewer counted 6; the count in the draft is 7.
- **Evidence that classification by reading works** (findings the name does not reveal):
  - `#count_heartbeats`, `#count_heartbeats!` and `guard_min_heartbeats` elaborate the wrapped command with `set_option maxHeartbeats 0 in` injected by the macro, hidden from Stage A (`Mathlib/Util/CountHeartbeats.lean`, lines 143, 187, 202). Without this finding, the O-3 rule would be trivially bypassable.
  - `#import_bumps` injects `set_option Elab.async false` and `set_option linter.minImports true`, hidden.
  - `#clear_deprecations` writes files (`IO.FS.writeFile`) and runs `lake build` (`IO.Process`).
  - `lrat_proof` accepts `include_str` (reads from disk).
  - `sudo set_option` accepts an undeclared option, outside the policy's option recognition.
- **Four points for the second reviewer** (non-blocking; the decision is recorded in the final TOML):
  1. `unset_option` (allowed): a sibling of `set_option`. There is no known bypass, because Stage A sees the literal `set_option` first, but the symmetry calls for a second opinion.
  2. `unsuppress_compilation` (allowed): the opposite of `suppress_compilation` (fail-closed); "forces compilation" is not trivially benign.
  3. `#lint` (allowed): premise recorded in the TOML: the linters are fixed Mathlib code at the pinned commit; if `#lint` starts accepting a user-chosen linter, it changes category.
  4. `#string_diagram` (ambiguous, allowed as a precaution): a candidate for the Phase 1 review.
- **L-25:** text approved without change. It goes into the commit of the final classification.
- **Phase 1 relaxation agenda:** recorded on the roadmap. There are 10 distinct items: the 9 ambiguous ones (which already include `#string_diagram` and `suppress_compilation`) and `#lint`.

## Instruction 18 round — second review of the Mathlib classification

- **Deviation from the checklist, recorded.** Step 3 requires the classification to be checked by a second reviewer who **is not the author** of the draft. An external review arrived without identification. The cited content existed, but the 4 line citations did not match the pinned commit (`#lint`: cited Frontend.lean 23–26, the text is at 42–45; `#string_diagram`: 35–37 → 51–52; `unset_option`: 20–23 → 43–45; `unsuppress_compilation`: 64–68 → 89–96). By the maintainer's decision, that review was discarded and **the second review was done by the author of the draft (Claude)**. It is not independent; the first reviewer must decide whether to accept it as such.
- **Decisions of the second review:**
  - `#lint` → fail-closed. `Batteries/Tactic/Lint/Basic.lean:131` runs the linter with `evalConstCheck`, and a file can define its own with `@[env_linter]` (Frontend.lean:42–45). The draft's premise ("fixed linters") was false.
  - `#string_diagram` → fail-closed, for consistency with the ambiguity rule. `Tactic.Monoidal.eval` is Meta normalization and does not execute compiled code; the vector "reduction triggers `implemented_by`/`native_decide`" claimed in the external review does not hold up in the source.
  - `unsuppress_compilation` → fail-closed (**a new finding**, which neither the draft nor the external review had seen). The form `unsuppress_compilation in cmd` expands to `… cmd suppress_compilation` (`Mathlib/Tactic/SuppressCompilation.lean:97–98`): it reinstalls, hidden from Stage A, the local elaborator that makes `suppress_compilation` fail-closed.
  - `unset_option` → allowed. It only erases the option (`(← getOptions).erase`, `UnsetOption.lean:38`).
- **Final result:** 60 `allowed`, 35 `metaprogramming`, 3 `syntax_extension`. The justification for each command is in a comment in the fork's `classification.toml`. L-25 received a paragraph with the three additions, and the Phase 1 agenda (roadmap) now includes `#lint` and `unsuppress_compilation`.

## Instruction 19 round (file `instrução17`) — smoke test passed, D-59, self-review statement

- **Milestone:** the third `auditor-prep` (run 39680033069) passed the smoke test: `Hydra.lean` with 20/20 `verified`, `exit_code` 0 and `unclassified` empty. Recorded in the CHANGELOG.
- **D-59: approved.** The fork `--check` accepts `.github/` and `.auditor/` (`FORK_PREFIXES`). Still in force: no `.lean`, ancestry and strict comparison of the closure.
  - **Tests:**
    - accepted with `.auditor/classification.toml` and `.auditor/allowlist.json`;
    - rejected: `README.md`, `.lean`, `.github/Gen.lean`, `.auditor/X.lean`, `.auditorx/a.toml`, an uncommitted change, a non-ancestor.
  - **Mutation:** going back to only `.github/`. L-24 updated.
- **Second review of the classification: self-review, the maintainer's final decision.** The 4 changes were approved (`#lint`, `#string_diagram`, `unsuppress_compilation` → fail-closed; `unset_option` → allowed). Final: 60/35/3.
- **Self-review statement (a transparency obligation):**
  1. **In `classification.toml`:** `reviewed_by = "author-self-review"`, `reviewer_independence = "none"` and `revision_note`. These are now keys validated by the generator, not a comment.
  2. **L-26** in `limitations.md`, with the given text and the mechanics.
  3. **In the report:** `tcb.classification_review_status`, mandatory in schema `1.1.0`.
  - **Tests:** the statement propagated up to the report (mini-project `author-self-review`; fixture 07 `core-only`); six classifications without a statement or inconsistent → exit 2.
  - **Mutations:** 6 (validation, consistency, propagation and the `core-only` status).
- **A finding from the same family as D-53, fixed with it:** the SHA-256 of `classification.toml` was also of the raw bytes. With a `classification.toml` committed in the fork, the allow-list's `--check` would diverge between a CRLF and an LF clone. Normalized, with a test and a mutation.
- **A finding from the same family, NOT fixed (proposal D-60):** `fingerprint.dependencies()` records `lake_manifest_sha256` of the manifest's raw bytes (`src/auditor/fingerprint/__init__.py`, `dependencies`). The report's fingerprint differs between a CRLF and an LF clone of the same commit. It does not affect the audit result, but it affects the reproducibility of the fingerprint. Proposal: use `normalize_newlines`, as in the other three hashes.
- **A bug in the fork's workflow (fixed in the fork):** in `auditor-prep`, `grep … | tee … || echo "nenhum sinal de ambiente"` never printed the line, because the `||` was decided by `tee` (always 0), not by `grep`. The `grep` result is now tested directly.
- **Origin of the discarded external review (the reviewer's question): still unanswered.** What is known from the document itself:
  - it began with an instruction to whoever would review the review ("Revise criticamente a resposta de segundo revisor abaixo…", i.e. "Critically review the second reviewer's answer below…");
  - the signature was "Segundo Revisor Independente" (Second Independent Reviewer), without a name;
  - the 4 citations carried correct text from the pinned commit, but at shifted lines (+16 to +25), consistent with quoting from memory, or from another version of the files, without the pinned commit's source open.

  This author does not know where the document came from (it was not produced in this session). The question was passed on to the maintainer; the answer, when it comes, goes here.

## Instruction 20 round (file `instrução18`) — measurement PRs; D-61, A2, D-62

- **Milestone (the reviewer's request):** 633 tests, 125/125 mutations after catching 1 real survivor, smoke test 20/20 and `auditor-prep` all green, with the allow-list byte-for-byte identical. Recorded in the CHANGELOG.
- **Result of the PRs (report `relatorio_camada2_medicao`):** all under 300 s, but none in steady state.
  - #2 trivial: 137 s cold; 126 s warm on the re-run.
  - #3 medium: probe `verified`; 10 `unresolved` because of `set_option backward.*`.
  - #4 fanout (`Set/Defs.lean`): 37/37 `unresolved` because of `syntax_extension_declared`.
- **A1 → D-61: approved and implemented.** The reusable workflow `auditor-warm-cache` + template, and `auditor-ci inspector`.
  - **Tests:** the same keys as `auditor-tier1` (Mathlib's with `github.sha` instead of `pull_request.base.sha`); the same runner; read-only; no comment, label or PR; the four paths of `auditor-ci inspector`.
  - **Mutations:** 6.
  - **Check in the real environment**, required by the reviewer: the workflow on the base, then a trivial PR with `cache_state: warm` and `inspector: hit`. Pending until the next push.
  - **Alternative rejected by the reviewer:** re-running the same PR as a measurement. A4 (`clock_origin: job_start` on the re-run) becomes moot.
- **A2: approved and implemented.** Restoring and saving the inspector cache in separate steps, with the save in `always()`, conditional on `auditor-ci inspector --check` = `built=true`.
  - **Tests:** the order of the steps and the conditions.
  - **Mutations:** 2 (without `always()`; without the build condition).
  - **Check in the real environment:** a PR red because of `unresolved`, followed by a re-run with `inspector: hit`.
- **A5 → D-62: approved and implemented.** The auditor is moved to `$RUNNER_TEMP/auditor-tool` after `pip install`; the default policy comes from there.
  - **Test:** no later step references `.auditor-tool` in the workspace.
  - **Mutation:** 1.
  - **Check in the real environment:** `project_dirty: false` in the next measurement's report.
  - `auditor-prep` (fork only) receives the same change.
- **A3 → L-27 (the reviewer's text) + a pending finding.** `Basic/Logic/Basic.lean`, chosen as fanout on the success path, does not declare syntax (empty grep, only docstrings), but has `simproc_decl` (lines 42 and 75). Stage A leaves it fail-closed, and the probe would come out `unresolved`. `Init.lean` (tertiary option) too: `register_linter_set`, `run_cmd`. Proposal in L-27: the criterion "Stage A with no unrecognized item". The first file that passes: `Mathlib/Lean/Name.lean` (position 3); the first outside `Tactic/`, `Lean/` and `Util/`: `Mathlib/Data/String/Defs.lean` (position 4).
- **PR #3 valid as a measurement.** The `backward.*` options went onto the Phase 1 relaxation agenda (`roadmap.md`).
- **Refinement (does not block Phase 0), proposed by the reviewer:** a measurement PR should distinguish `measurement_result: success | fail-closed-path`, so as not to signal failure when the result is the expected one. Today, `exit_code` 1 covers `unresolved` without `infra_failed`, and the job turns red.
- **L-28 (native evaluation):** 0 real uses in Mathlib `e1b2403b`; the 2 lexical cases are false positives.
- **A new finding, no decision requested yet:** Stage A treats any token at column 0 as the start of a command. Terms that continue a command at column 0 (`match … with`, `do`, `f!"…"`) come out `unknown_command`. Seen in `Mathlib/Lean/Meta/Simp.lean:32`, `Mathlib/Tactic/MkIffOfInductiveProp.lean` (lines 176, 195, 216, 229) and `Mathlib/Tactic/SplitIfs.lean:32`. It is fail-closed, therefore safe, but the checklist treats `unknown_command` as an incomplete allow-list. It is actually a lexer false positive, not an unclassified command.
- **Explanation of `inspector: miss` with the file `hit` (caveat of the previous report):** the cache signal is measured before the inspector's pre-build (`_prebuild_inspector`); the file's field is measured after it. Both are right: the first says the cache came cold, the second that the file did not pay for the compilation.
- **Origin of the discarded external review:** asked of the maintainer three times, without an answer. Recorded without blocking, as instructed by the reviewer. If Phase 1 needs a real independent review, knowing what failed in the first attempt will matter.

## Instruction 22 round (file `instrução20`) — Phase 0 closed with conditions

- **Origin of the discarded external review: answered by the maintainer.** It was another AI, **without access to the source code**. Diagnosis: the 4 citations had the right text, but at shifted lines (+16 to +25). This is consistent with prior knowledge of the files (another version, or memory), without the pinned commit's source open. The failure of the first attempt at an independent review, diagnosed: **a reviewer without the source at the pinned commit**. Consequences for Phase 1's independent review:
  - the reviewer receives the source at the pinned commit (`e1b2403b` or the current one), not descriptions or excerpts;
  - every citation carries file, line and the commit's SHA;
  - citations are checked mechanically against the commit before the review is accepted: a line that does not match invalidates the citation, as happened here;
  - the reviewer identifies themselves (a person, or a model and session), with their degree of independence declared (`reviewer_independence`).
- **Step 9 found a real bug in `auditor-report`** (the API's non-deterministic `head_sha` filter). Fixed in the template; details in `maintenance.md`, "Reference tests for the CI failure modes".
- **Step 8 passed on the first try:** a file timeout → exit 2, `infra_failed`, green job, label `auditor-failed-infra`, PR mergeable.

## Instruction 24 round (file `instrução22`) — Phase 0 closed unconditionally

- **Pending item from the discarded external review: CLOSED.** Asked 3× and answered on 2026-10-22: another AI, without access to the source, line shift +16 to +25. Rules for Phase 1's independent review recorded in roadmap.md. Pending item closed.

## Known GitHub API quirks

A record for whoever builds similar workflows (instruction 23).

- **The `head_sha` filter of the GitHub Actions runs API is not deterministic.** The same query, repeated in sequence, alternates between 0 and 1 result. This holds for the three endpoints: `/repos/{repo}/actions/runs?head_sha=…`, `/actions/workflows/{file}/runs?head_sha=…` and `/actions/workflows/{id}/runs?head_sha=…`. Listing **without** the filter was stable in every repetition. `gh run list --commit` uses this filter and inherits the problem, in any version (tested: 2.101.0 and 2.103.0).
  - Evidence (2026-10-22, `Enzo47961/mathlib4`, `total_count` per endpoint, in the order file / id / repository):
    - commit `769e23c` (run 39813522377, completed): 0 / 1 / 1;
    - commit `d585660`: 1 / 1 / 1;
    - commit `dd08fb8` (run 39760172227): 1 / 0 / 1;
    - six repetitions for `769e23c` (columns: file, id, repository and, as a control, the commit's `check-runs`): `1 1 1 1`, `1 1 1 1`, `1 1 1 1`, `1 1 0 1`, `1 1 0 1`, `1 1 1 1`.
  - Observed effect: `@auditor report` answered "no run" for an audited commit (step 9, run 39818084000).
  - Workaround adopted in `auditor-report.yml`: list recent runs without a filter and select `head_sha` on the client, with the SHA validated as 40 hex characters before it enters `jq`.

## Instruction 23 round (file `instrução21`) — qualification in the summary

- **The line `classificação: … (L-26)` in the summary** (Job Summary and the `@auditor report` comment), before Phase 0's unconditional closure. Reason, from the reviewer: L-26 exists so that the statement travels with the claim; an exception for "a comment on a fork PR" opens the door to the next one. The value comes from each report's `tcb.classification_review_status`; without a readable report with the field, the line says "indeterminada" (undetermined), and never disappears.
- **Comments on PRs #1-#9 are legacy; the author-self-review qualification is mandatory on any new comment.** In practice, only PR #8 has `@auditor report` comments that predate the line: the one from step 9's first attempt, which carries no result, and the one from the second, which carries the summary without the line. Updating them is optional and outside the closure (`roadmap.md`).

## Fixes made on resumption (Windows session)

- The Stage B and Q5 code from the previous session was not preserved: only `stage_a.py` (already with project allow-list support) and the documents. Q5 and Stage B were re-implemented from the recorded decisions.
- Portability: Lean's output is now decoded explicitly as UTF-8 (on Windows, the default is cp1252, which broke two ground-truth tests with Unicode names).
