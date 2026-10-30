# Limitations (Phase 0, Tier 1)

Normative reference for the tests: each limitation has an identifier `L-n`, cited by the tests that depend on it. A limitation here is something the tool **knowingly does not cover**; it is never a reason to emit `Validada` (validated).

"Instruction N" refers to the numbered decisions of the project's external reviewer. Status values (`Validada`, `Rejeitada`, `Não resolvida`, `Conforme`, `Não conforme`, `Não resolvido`, `Não auditada`) are quoted as the tool prints them; see the README for their meaning.

## L-1. The kernel and the compiler are in the TCB, not audited
The Lean kernel is a trust anchor. With `native_decide`, trust extends to the compiler and to every implementation reached through `@[implemented_by]`. Scenario 04 demonstrates the risk: a lying implementation makes it possible to derive `False` (`tests/conformance/04-implemented-by/GroundTruth.lean`). That is why the combined pattern is `Rejeitada` (rejected).

## L-2. Stage A is a lexical scan, not parsing
Lean's syntax is extensible, and the parser depends on imported notations. Stage A:
- **only sees the text of the target file**. A transitive `sorry` (scenario 02) and an import cycle are invisible to it; Stage B covers them;
- **checks commands only at column 0**. A token at column 0 that is neither on the allow-list nor among the continuation tokens (`|`, `where`, …) results in `unknown_command` (fail-closed). Consequence: a legitimate continuation written at column 0 produces a false "unrecognized" (an inconvenience, never a false seal). Indented commands do not go through this check;
- **detects risky commands in any position** (`macro`, `notation`, `run_cmd`, `#eval`, …). They are reserved Lean tokens and cannot be identifiers, except between `«»`. Risky commands whose token is a **symbol** (`?`, `$`) are only detected at the start of a command (column 0): the symbol appears in terms (`?_`, `?m`, `f $ x`) and is not reserved (D-56);
- **accepts `module` only as the file's first token** (the v4.36 module-system header, before the `import`s). In any other position, `module` is `unknown_command` (D-57);
- **only knows project commands with a project allow-list** (Q5). Without `<project>/.auditor/allowlist.json`, Mathlib commands (`lemma` and others) result in `unknown_command`. The Mathlib allow-list is layer-2 evidence, generated in the fork (see `docs/maintenance.md`), and does not block layer 1;
- sees `decide +native` and `native := …` only as candidates. The evidence is Stage B (`Lean.ofReduceBool`, or v4.36's native auxiliary axiom);
- does not inspect the contents of interpolated strings (`s!"{…}"`).

The allow-list is versioned per toolchain and tested against it (see `docs/maintenance.md`).

## L-3. `set_option` and comments are only visible to Stage A
They are not recorded in the elaborated environment. The `maxHeartbeats 0` exemption is only recognized in the form `set_option maxHeartbeats 0 in <declaration>`.

## L-4. `native_decide` justification by docstring (O-1, option B)
- **Strict grammar.** Exactly one line in the docstring of the owning declaration, in the format
  `auditor_justified: reason="<text>" reviewer="@<handle>"`.
  No escaping (`\` or `"` inside `reason` is forbidden), no multi-line continuation, no duplicate. `<handle>` uses letters, digits and hyphens. Any deviation results in `native_decide_justification_malformed`. The only normalization is removing trailing whitespace, because Lean stores the docstring with the space before `-/` (checked in the O-1 investigation).
- **Attribution by name, dependent on an internal convention.** The owning declaration is obtained by removing the internal components from the name of the constant that references the native-evaluation axiom directly (`Lean.ofReduceBool`/`Lean.ofReduceNat`, or v4.36's auxiliary `…._native.native_decide.ax_N`; e.g. `nd_justified._proof_1_3` → `nd_justified`). This convention is a compiler detail and may change between Lean versions. If the owner is not resolved, the result is `Não resolvida` (unresolved) with reason `native_decide_owner_unresolved`.
- **A justification is not authentication.** Any author can write the line. Approval by the designated reviewer is human and out of scope.
- **`where` auxiliaries.** On v4.22, the `native_decide` of a `where` auxiliary (e.g. `outer.aux`) went through `outer._proof_N`, and the owner was `outer`. On v4.36.0-rc1, the auxiliary axiom is named `outer._native.native_decide.ax_1_1` (a name derived from the top-level declaration), but what references it is `outer.aux` itself: the owner becomes `outer.aux`, which is where the `native_decide` is written. Behaviour observed on the pinned toolchain and locked by a test (`tests/stage_b`, fixture `edges`).
- **Visibility.** The line appears in documentation generated from docstrings.
- **Fallback recorded, not adopted.** If Mathlib objects concretely to the structured line in docstrings, the alternative is option (C): a structured comment, an external `justifications.toml` file, or `native_decide` always a violation in Phase 0. There is no preventive migration.

## L-5. `@[implemented_by]` alone is only a candidate
The tool does not check equivalence between a definition and its implementation. The attribute without native evaluation on the kernel's path results in `Não resolvida` (`implemented_by_candidate`), not in `Rejeitada`.

## L-6. Unicode: confusables are only a warning
Bidirectional controls and zero-width characters are fail-closed in any position, including comments, strings and `«»` names. Lean accepts zero-width characters inside `«»`, and the kernel validates the declaration without axioms (fixture `tests/fail-closed/namespace-unicode`).

Confusables (TR39 16.0.0) produce a warning, never a failure, in two cases:
- two identifiers **in the same file** with the same skeleton and different spellings (e.g. `hi` and `hι`). Single-character components are ignored, because `a`/`α` is a mathematical convention;
- a non-ASCII `«»` name whose skeleton is ASCII.

Imported identifiers are not compared. Lean does not accept Cyrillic in identifiers without `«»` (checked), so the practical surface is Greek and `«»` names.

## L-7. `Classical.choice` is allowed
Constructive contexts are a Phase 3+ topic. An explicit decision, not an omission.

## L-8. `maxHeartbeats 0` is hygiene, not integrity
It invalidates only the declaration that uses it. Declarations that depend on it keep their own state; the dependency appears in `depends_on_rejected`. See objection O-3.

## L-9. Correspondence is not audited
`correspondence_status` is always `"Não auditada"` (not audited). A theorem that proves the wrong thing can receive `Validada` + `Conforme`.

## L-10. A fingerprint is not revocation
The report states the fingerprint; comparing it with the current environment is the consumer's responsibility. Revocation is Phase 1.

## L-11. The timeout test is artificial
The `auditor-failed-infra` path is tested with a reduced limit and declares `timeout_test: artificial` in the report. Real latency only comes from measurements on Mathlib PRs (layer 2 of Done). The 90 s per-file timeout and the 15 min extended budget are initial values, not measured: the layer-2 per-file p95 decides the default (instruction 11).

## L-12. Coverage of the builder's environment
Without access to the Mathlib cache, the development environment only checks fixtures without Mathlib. Real measurements and the test of the Action in a fork are evidence brought by the maintainer.

## L-13. `@[extern]` and toolchain implementations
O-5 accepted: `@[extern]` goes in the same category as `@[implemented_by]`, with its own scenario (`04b-extern`). The ground truth confirms the risk: a user `@[extern "lean_nat_add"]` on a definition that multiplies lets `native_decide` prove `myF 2 3 = 5`, and the kernel proves the negation without axioms (`False`).

The toolchain's own functions also use these attributes: every `native_decide` on `Nat` goes through the core's `@[extern]` (`Nat.add`, `Nat.decLt`, `Nat.ble`), and every `sorry` pulls in the core's `@[implemented_by]` (`Lean.Name.str`). Under Q7 (option a), these implementations are TCB and do not trigger the rules; only user-level ones do. The boundary is declared by the toolchain, restricted to the allow-list of roots used by the target project (D-42), and by `lake-manifest.json` (`docs/tcb.md`). The canary is scenario `06-tcb-boundary`, with one declaration per root of the allow-list.

`partial def` does not appear as `@[implemented_by]` on the pinned toolchain (checked in the `edges` fixture).

## L-14. The inspector is in the TCB
The inspector (`src/auditor/lean/Inspect.lean`) is trusted code: if it omits a declaration or an axiom, the aggregator has no way of knowing. Mitigations:
- its own dependency closure is compared with `Lean.collectAxioms` (the `#print axioms` algorithm); a disagreement becomes `inspector_disagreement` (fail-closed);
- referenced constants missing from the environment, which the official algorithm silently ignores, become `missing_constants`;
- the Stage B tests compare the results with `#print axioms` run by Lean itself, in a separate process;
- the hashes of the source and of the binary enter the TCB and the fingerprint.

`type_hash` and `value_hash` use Lean's `Expr.hash`: a 64-bit structural hash, deterministic but not cryptographic. The composition of the report's `declaration_hash` will be fixed in the Schema step.

## L-15. Selection of the reported declarations
The report covers the constants of the target module that have a declaration range in the source and a user name (private ones included). Generated auxiliaries (`match_N`, `_proof_N`, recursors, `noConfusion`, equations) are left out, but appear in the closures of those that use them. Generated constants with a range in the source are included: a `structure`'s constructor and projections, anonymous instances, and the parser created by `macro` (`tacticObviously`).

## L-16. The project allow-list is only checked against the pin
Phase 0 checks that the project allow-list corresponds to the pinned environment (`env_pin` = `lean-toolchain` + bytes of `lake-manifest.json`), not that the classification of each command is semantically correct for the target. Semantic correctness of the allow-list is Phase 1+.

The pin does not cover the project's own source code. A command that the project redefines between generation and audit keeps the old classification. A new project command falls into `unknown_command` (fail-closed). Syntax coming from imports is covered by Stage B (L-2).

## L-17. Criterion for `#…` commands and other elaboration commands (Q8)
**Amended by L-33a (Phase 1):** the criterion applies to a command, tactic, term or attribute. Original text, for the record:

**Normative criterion:** a command is fail-closed in Stage A if it **can execute compiled code at elaboration time, before Stage B can inspect the environment**. Future decisions about commands must be derived from this criterion, not from case-by-case research.

**Why this criterion.** A malicious `@[extern]` or `@[implemented_by]` in user code can perform I/O during elaboration, before any audit. Blocking these commands is defence in depth against **pre-audit execution**. Axiom corruption is not the target here: it is covered by Stage B, which inspects the elaborated environment.

Application on the pinned toolchain (`classification_version = "3"`):

| Command | Decision | Reason |
|---|---|---|
| `#eval`, `#eval!` | fail-closed | executes compiled code |
| `#reduce` | fail-closed | treated like `#eval` by the reviewer (D-1) |
| `#guard`, `#widget` | fail-closed | call `evalExpr` (checked in the toolchain's source) |
| `#guard_expr` | fail-closed | evaluates the expression at elaboration time |
| `#check_tactic`, `#check_tactic_failure` | fail-closed | run user tactics, which can call `evalExpr`: they bypass the `#eval` block |
| `#check` | allowed | only checks a type; executes nothing |
| `#synth` | allowed | typeclass synthesis is unification; does not execute `@[extern]` |
| `#check_simp` | allowed, **reviewed** | a `simp` diagnostic: reduces terms, does not execute compiled `@[extern]` |

`#check_tactic_failure` was not mentioned in decision Q8. It was included by direct derivation from the criterion, because it runs a user tactic exactly like `#check_tactic`.

Limit: the criterion covers commands that **appear in the target file**. Code executed during the elaboration of **dependencies** (for example, `initialize` in an imported module) runs when `lake build` compiles those dependencies, and that is outside the reach of the target's Stage A (L-2).

## L-18. The CI clock and `cache_state` are runner measurements
- The PR clock starts at `pull_request.updated_at`, the event's timestamp on GitHub, and is compared with the runner's clock; clock skew between the two enters the measurement. On a re-run, the clock starts at the beginning of the job (D-30), and the earlier queue time is not counted.
- `cache_state` depends on two signals (restoration of `~/.cache/mathlib` and of the inspector binary). A cache that is restored but useless (for example, `.ltar` files from another toolchain) counts as warm; the extended budget is never granted without a cold signal (D-31).
- Hash pinning in CI covers the actions and elan. The Lean toolchain downloaded by elan and the Python dependencies resolved by pip are not hash-checked in the job; their effective versions are recorded in the report's TCB (D-35).

## L-19. The native-evaluation auxiliary axiom is recognized only by its shape (v4.36, Q9)
On `leanprover/lean4:v4.36.0-rc1`, `native_decide` no longer produces `Lean.ofReduceBool`: it adds, per use, an auxiliary axiom `<owner>._native.native_decide.ax_N : e = true` (`Lean.Meta.nativeEqTrue`), which the kernel does not re-check. The inspector recognizes it by its shape (`native_auxiliary`); the policy treats it as native evaluation for the justification rules and for the combined pattern, and **additionally** leaves the premises `Não resolvido` (`native_auxiliary_axiom`), because the shape does not prove the origin. A hand-written `axiom` with the same name and type is indistinguishable in the environment (demonstrated in the `edges` fixture: `uses_spoof`). An imported tactic (from another file of the PR, or from a dependency) can also add an axiom of this shape without the target file's Stage A seeing anything. That is why the recognition only serves to give the precise reason and to apply the stricter rules (justification, combined pattern); it never leads to `Validada`/`Conforme`.

**Decision (Q9, option a, instruction 13): permanent in Phase 0.** `native_decide` never comes out `verified` in Phase 0. v4.36 showed that certifying it would depend on internal compiler details that change between versions, and Phase 0 is designed to be stable across toolchain bumps. Re-evaluation by the kernel is a Phase 1 research item (`docs/roadmap.md`). Impact measured on the pinned Mathlib (`e1b2403b`): no proof in the `Mathlib` library uses native evaluation, which Mathlib's own linter forbids; usage is confined to `MathlibTest`. Mathlib's `inclusion` tactic calls `nativeEqTrue` with `+native`, and the axiom it generates (`…._native.inclusion.ax_…`) is treated the same way. The per-PR measurement is in layer 2 (`tools/layer2/native_usage.py`).

## L-20. Axioms precomputed in `.olean` files are not checked
Since v4.36, the `#print axioms` that a human runs uses, for imported declarations, an axiom summary recorded in each `.olean` at compile time. The auditor does not use this summary (D-39): it walks the bodies. Nor does it compare the summary with its own walk, because the extension state is private to Lean's module. A divergent summary (a tampered or stale `.olean`) is not detected as a divergence; it does not affect the auditor's result, but it can make a human's `#print axioms` disagree with the report.

## L-21. Phase 0 is Mathlib-oriented: `target_trusted_roots` comes from Mathlib's closure
Phase 0 is Mathlib-oriented. `src/auditor/data/target_trusted_roots/<toolchain>.json` is the import closure of the pinned Mathlib (`e1b2403b`: `Init`, `Lake`, `Lean`, `Std`). Lean projects other than Mathlib must generate their own `target_trusted_roots` with `tools/gen_tcb_roots.py`. Modules from roots not used by the target are classified as user-level and trigger the `@[extern]`/`@[implemented_by]` rules. This is the correct fail-closed behaviour, but it may produce false positives on targets other than Mathlib (for example, a project that legitimately uses `LeanIR`). Automatic root discovery for arbitrary targets is on the Phase 1 roadmap.

## L-22. `fanout.py` is not tested against Mathlib in the suite
The suite does not download Mathlib. That is why `tools/layer2/fanout.py` (D-38) is tested only with synthetic graphs (`tests/maintenance/test_layer2_tools.py`), not against the real Mathlib. The choice of the highest-fanout file is checked against the pinned commit at measurement time, with `--expect-commit` (layer-2 checklist, step 6), and the output records its provenance (commit, SHA-256 of `lake-manifest.json`, `lean-toolchain`). The same holds for `tools/layer2/native_usage.py` and for the `--check` of `tools/gen_tcb_roots.py` (checklist, step 3).

## L-23. Layer 1 runs in the author's environment; cross-environment bugs only show up in layer 2
The layer-1 tests run in the author's environment. Bugs that only appear when crossing environments (CRLF/LF line endings, collisions between libraries of the same build, cache state, the runner's shallow checkout) only show up in layer 2. That is what happened on the first `auditor-prep` (instruction 15): D-52 (the extraction imported Mathlib's `Cache` library together with `Mathlib`), D-53 (the `lake-manifest.json` hash computed in a CRLF clone) and D-54 (`--check` without a fork case). None of the three was detectable in layer 1: the fixtures had a single library, the suite ran only on Windows, and `--check` had never seen a fork. **Layer 2 is not optional for considering the work done: it is a distinct category of test.**

## L-24. `gen_tcb_roots.py --check` accepts a measurement fork (a layer-2 relaxation)
`--check` accepts a `HEAD` different from the commit recorded in `target_trusted_roots` (D-54) when, and only when: (a) the recorded commit is an ancestor of `HEAD`; (b) the working tree differs from it only in `.github/` and `.auditor/`; and (c) no `.lean` file changed, not even inside those two prefixes. The invariant that matters is "no `.lean` changes"; restricting to the two prefixes is the strict proxy. `.auditor/` is included because step 3 of the checklist commits the allow-list and the command classification there (D-59): it is only auditor configuration, which does not enter the import closure. The relaxation exists for the measurement in the fork (`auditor-base` = `e1b2403b` + the auditor's workflows and configuration). Outside that case, the check remains strict: same commit, and the data (roots, closure, packages, manifest hash) compared byte for byte. In the real repository, in production, the strict check applies. In a shallow checkout, the recorded commit must be present (in the fork's CI: `fetch-depth: 20`); if it is not, ancestry is not proven and the check fails.

## L-25. Classification of Mathlib commands: fail-closed in ambiguous cases
The classification of Mathlib's 98 commands (the fork's `.auditor/classification.toml`, Mathlib `e1b2403b`) marks as fail-closed every command whose effect could not be determined with certainty by reading its definition: commands with network IO (`#leansearch`, `#loogle`, `#search`), wrappers that rewrite the command (`#deprecate`, `deprecate`), macros that inject hidden options (`#import_bumps`), the local elaborator registration of `suppress_compilation`, and diagnostics that display arbitrary proofs (`#explode`). The classification may be relaxed in Phase 1 with evidence (a reviewed reading of the implementation at the pinned commit, and a test that demonstrates no effect on the environment that Stage B audits). Until then, files that use these commands do not come out `verified`.

In the second review, the following also became fail-closed: `#lint`, which runs linters defined by the file itself (`@[env_linter]`); `unsuppress_compilation`, whose `in cmd` form reinstalls `suppress_compilation`'s elaborator; and `#string_diagram`, for being ambiguous. Result: 60 `allowed`, 35 `metaprogramming`, 3 `syntax_extension`.

## L-26. The classification review is a self-review in Phase 0
The classification of Mathlib's 98 commands was written and reviewed by the same author. An external review was attempted and discarded for lack of identification and for divergent line citations. Any report, measurement PR or public coverage claim must declare `classification_review_status: author-self-review`. Phase 1 must include an independent review before any claim of Mathlib coverage in an external context.

Mechanics (instruction 19): the project `classification.toml` requires `reviewed_by` (`author-self-review`, `human-reviewed` or `independent-ai-reviewed`) and a consistent `reviewer_independence` (`none` for self-review, `independent` for the others), plus an optional `revision_note`; without them, the generator refuses (exit 2). The generated allow-list keeps the declaration (`classification_review`), and every report repeats it in `tcb.classification_review_status` (a mandatory field of schema 1.1.0, included in the fingerprint). Without a project allow-list the value is `core-only`; with a project allow-list without a classification, `no-project-classification`; with an allow-list from an old generator, without the declaration, `undeclared`. Self-review allows measurement PRs and internal claims accompanied by the declaration; it does not allow presenting Mathlib coverage to third parties (Zulip, paper, blog) without qualifying it as self-reviewed.

## L-27. Fanout measurement: the success path and the fail-closed path are separate categories
**L-27.** The fanout measurement on the success path uses the highest-fanout file whose Stage A has no unrecognized item. The criterion "no declared syntax" is insufficient: files such as Basic/Logic/Basic.lean use simproc_decl, Init.lean uses register_linter_set and run_cmd, and both fail closed for a reason other than syntax. The criterion "clean Stage A" is the only one that guarantees the success path, and it is reproducible in Phase 1 (the same verification algorithm).

Files that Stage A does not accept are measured on the fail-closed path, a separate category. The distinction comes from the architecture, not from the tool.

Earlier wording (instruction 20), replaced by this one in instruction 21: "The fanout measurement on the success path uses the highest-fanout file among those that do not declare syntax. Files that declare syntax are measured on the fail-closed path, a separate category."

Origin (instruction 20): the suggested highest-fanout file, `Mathlib/Data/Set/Defs.lean` (position 20, 8092 dependents), declares `syntax`, `macro` and `prefix`. Under L-17, every declaration of the file comes out fail-closed, including the probe lemma. It is still measured, as "fanout, fail-closed path" (PR #4: `unresolved` 37/37, audit 6.5 s).

**Finding when applying the earlier wording (it motivated the amendment):** "not declaring syntax" is not enough for the success path. The two files indicated also come out fail-closed in Stage A, because of metaprogramming:
- `Mathlib/Basic/Logic/Basic.lean` (position 24): no syntax, but `simproc_decl` on lines 42 and 75;
- `Mathlib/Init.lean` (position 1): `register_linter_set` and `run_cmd`.

A scan of the top 60 positions of the ranking with Stage A and the fork's allow-list: 19 files with no unrecognized item. The first is `Mathlib/Lean/Name.lean` (position 3, 8153 dependents); the first outside `Tactic/`, `Lean/` and `Util/` is `Mathlib/Data/String/Defs.lean` (position 4, 8147). That is, 41 of the 60 (68 %) come out fail-closed in Stage A (Phase 1 agenda in `roadmap.md`).

**Choice (reviewer, instruction 21):** `Mathlib/Data/String/Defs.lean` (position 4, 8147 dependents). It is the first clean file outside `Tactic/`, `Lean/` and `Util/`, the same exclusion criterion as the medium PR. `Mathlib/Lean/Name.lean` (position 3) is a Lean meta-tool: it only enters as an additional measure of "strictly highest clean fanout", never as a substitute.

## L-28. A lexical search for native evaluation overestimates
A lexical search for `native_decide` overestimates: it matches text inside metaprogramming. The real measurement requires semantic inspection (Stage B), which is what the tool does. Result: 0 real uses in Mathlib@e1b2403b.

Data (instruction 20): `tools/layer2/native_usage.py` flagged 2 of 256,505 declarations of the `Mathlib` library (0.0008 %), both in `Mathlib/Tactic`, and both are false positives checked by hand:
- the linter that forbids `+native` and `native_decide` (`Mathlib/Tactic/Linter/DeprecatedSyntaxLinter.lean`, syntax patterns on lines 138 to 145);
- the copy of a configuration field, `native := options.native`, in the `inclusion` tactic (`Mathlib/Tactic/Inclusion/Core/Elab.lean:348`).

In the 7 layer-2 reports (first run and measurement PRs), no declaration has `native_auxiliary_axiom` among its reasons. The measurement validates Q9 retroactively: the permanent fail-closed of `native_decide` costs almost no coverage in the main library, because the construct is not used there.

## L-29. `@auditor report` from someone without access: not tested end to end
Step 9 tested the @auditor report flow triggered by an OWNER. It did not test the path of a comment from someone without access — the guarantee is the author_association condition, locked by a unit test, not tested end to end in layer 2. An end-to-end test requires a second account; it remains an information gap, non-blocking.

Origin: instruction 23. The condition is in `ci/templates/auditor-report.yml` (`author_association` in OWNER, MEMBER or COLLABORATOR) and is locked by `test_report_workflow_requires_explicit_human_request`. The end-to-end test is on the Phase 1 agenda (non-blocking).

## L-33. User code executed during elaboration by a tactic or term was not detected by Stage A
**Phase 1 finding (P0-2, 2026-10-22).** L-17 made fail-closed only the *commands* that can execute code during elaboration, before Stage B.

**Demonstration**, on the pinned toolchain (`leanprover/lean4:v4.36.0-rc1`):
- `run_tac do (IO.FS.writeFile "marker" "x" : IO Unit)` (tactic) and `by_elab do …` (term) wrote a file during the file's `lake build`;
- Stage A recorded nothing;
- the auditor gave `verified`, exit 0.

**Nature of the gap:** integrity, not coverage (reviewer, instruction 24). The PR's code runs on the runner, as the same user that has the cached inspector and the installed auditor, and Stage B does not see the execution: the Lean environment does not change, only the file system.

**Response: amendment L-33a, implemented in Stage A v4 and inspector v5.** Inventory with sources in `docs/l33-inventory.md`.

## L-33a. Amendment of L-17: command, tactic, term or attribute
**Amended normative criterion (instruction 24):** a command, tactic, term or attribute is fail-closed if it can execute user code at elaboration time, before Stage B can inspect the environment. The original L-17 covered only commands.

**Application** (`docs/l33-inventory.md`):
- **Execution on the spot, lexical:** `run_tac` and `by_elab`, in any position.
  - Result **`Rejeitada`** (`elaboration_executes_code`, in `policy_violations`): the execution is a concrete violation, not an ambiguity.
  - It applies to every declaration of the file, because the execution happened in the build that Stage B audits.
- **`unsafe`, lexical:** in any position, `Não resolvida` (`unsafe_code`). It hides IO in a pure type, executed if a term is evaluated during elaboration (tactic configuration, `include_str`, `eval%`).
- **From the environment** (inspector v5): every constant of the target module whose **type** reaches `IO.RealWorld` (an elaborator, tactic, simproc, attribute handler, `initialize` procedure), or that carries `@[extern]`, leaves the file `Não resolvida` (`target_defines_executable_code`).
  - Registering does not prove that it executed.
  - There is no list of attribute names: the type decides.
- **A dependency changed in the PR:** a target that imports (the inspector's import closure) a changed file with `run_tac`/`by_elab` (or an unreadable one) comes out `Não resolvida` (`dependency_executes_code`). `auditor-ci` passes the changed files to each audit (`--changed`).
- **`show_panel_widgets`** moved from `allowed` to `metaprogramming` (core classification v5): it evaluates terms of the file, like `#widget`. The core risk classification now applies on top of a project allow-list generated earlier.

**Declared limits:**
- **An integrity gap (instruction 25), not a coverage gap: a changed dependency that only registers code** (through an attribute, `initialize`, `unsafe`), without `run_tac`/`by_elab`.
  - It itself comes out `Não resolvida` as a target, but the target that imports it **comes out `verified`** even though the registered code ran during its build (a dependency's `initialize` runs when the target is compiled: scenario 10).
  - It is the same pattern as the transitive `sorry`. The fix, `dependency_registers_code`, detects in the target's environment the code registered by a changed dependency.
  - It is a **Phase 2 P0 item** (`roadmap.md`). Mitigation (b) does not close it: it detects tampering, not execution.
- **CLI without `--changed`:** it does not cross dependencies (`auditor check` on its own). `auditor-ci` always passes the list.
- **Mathlib's external dependencies** (Batteries, Aesop, Qq, ProofWidgets, Plausible, LeanSearchClient, importGraph) have not been inventoried. The environment-based defence applies to the target's code, wherever the attribute was defined.
- **A `lakefile.lean` changed in the PR** executes code during `lake build`: outside Stage A's reach.
- For all these cases, and for any mechanism outside the inventory, the defence is the **structural mitigation (b)**: hashing the inspector and the auditor before and after `lake build`, `toolchain_tampered`. It detects tampering, not execution: (a) and (b) are different defences, and both are needed.
- **(b) implemented** (instruction 25, scenario 11) and **approved** (instruction 26). The first version had 3 errors, caught by the suite before any mutation (budget consumed by hashing, a test of the old order, an empty variable in the control): evidence that the suite works (`maintenance.md`). What it does **not** cover:
  - tampering with the Lean toolchain (`~/.elan`), with Python or with other runner dependencies;
  - tampering that is undone before the check;
  - reading or exfiltration (the hash detects writes, not reads).

## L-30. Stage A fail-closed rate on the top-60 by fanout (P0-2)
The Stage A fail-closed rate on the top-60 is 65.0% after (a); a ceiling of 53.3% even relaxing everything; Mathlib coverage is blocked until Phase 2.
- 39 of the 60 fail: 18 only because of syntax, 7 only because of a non-syntactic command, 14 for both reasons. 32 declare genuine syntax, which instruction 24 keeps fail-closed.
- Without relaxing `run_cmd`, the ceiling is 56.7 %.
- The P0-2 kill criterion (> 50 % after (a) and (b)) is met.
- **Additional measure, which does not replace the gate:** over the whole `Mathlib` library, the rate is 14.4 % (1244 of 8651). The dominant cause is `notation` (553 files), a toolchain-generated macro. If toolchain-generated `notation` can be recognized as TCB (the same logic as P0-1's `ctorIdx`), the rate drops a lot. A question for Phase 2 (`roadmap.md`).
- Official re-measurement with Stage A v4 (L-33a), run 39849624202: top-60 unchanged (65.0 %); whole of Mathlib 14.8 % (lexical `unsafe` in 74 files). L-33a's environment-based detection is not in these numbers (`docs/p0-2-fail-closed.md`, section 8).

## L-35. Coverage cost of L-33a: delaborators and tactic extensions in mathematical files
L-33a's environment rule (`target_defines_executable_code`) leaves the whole file `Não resolvida` when the target module defines code capable of running during elaboration. In mathematical files, this hits delaborators and `positivity` extensions. **Fail-closed is correct:** this code runs during elaboration. But it has a coverage cost, which 1b did not catch (none of the 35 sampled files had a delaborator). Found during the 1c selection (`docs/user-study.md`, section 8).

**Measurement** (`auditor-measure`, option `l35`, run 39970204221; Mathlib `e1b2403b`, same criterion as inspector v5; per-module data in `docs/l35-measure.json`):

| Slice | Modules | Reportable declarations |
|---|---|---|
| Flagged by the rule (gross) | 686 (7.93 %) | 30,252 (9.14 %) |
| … with a hand-written constant (`@[delab]`, `@[positivity]`, `elab`…) | 550 | 21,337 |
| … with only a generated delaborator (`_aux_…_delab_app_…` from `notation`) | 136 | 8,915 |
| **Marginal cost** (Stage A accepts the file; it falls only because of L-33a) | **242 (2.80 %)** | **11,269 (3.41 %)** |
| … of which in mathematical files (outside `Tactic`/`Util`/`Lean`/`Linter`) | 122 | 9,037 (2.73 %) |
| …… delaborator | 74 | 4,691 |
| …… `positivity` extension | 35 | 3,618 |
| …… others (`norm_num`, elaborators, `evalX` from `match`) | 13 | 728 |

Three readings:
- **The cost that L-33a adds is the marginal one, 3.41 %** of declarations; the gross figure (9.14 %) includes files that Stage A already leaves `Não resolvida`. It is less than half of `ctorIdx` (L-34, 7.35 %).
- **Generated delaborators: zero marginal cost.** The 136 modules that have only a generated delaborator already fall in Stage A because of the `notation` command itself (`syntax_extension_declared`). Recognizing the generated delaborator as TCB, on its own, recovers no declaration. It only recovers them together with the treatment of `notation` in Stage A.
- **All of the marginal cost comes from hand-written code** (delaborators, `positivity` extensions, elaborators). Under nuance (iii) of instruction 28, a hand-written delaborator is user code, and fail-closed is correct. Recovering this coverage would require a different policy, which the project has not decided yet.

**In 1c:** it is a known cause (instruction 28, Q2 (ii)), with its time measured separately. **Classification:** roadmap (instruction 29). The generated delaborator enters as a consequence of the P0 item "`notation` in Stage A" (`roadmap.md`).

## L-34. An attribute generated during elaboration brings down 7.35 % of Mathlib's declarations (P0-1)
An attribute generated during elaboration causes fail-closed in 7.35% of declarations; the TCB policy for generated code needs revision in Phase 2.

**Measurement** (`auditor-measure`, run 39845428621; `docs/p0-1-implemented-by.md`): of the 330,852 reportable declarations of Mathlib `e1b2403b`, 24,322 (7.351 %) come out `Não resolvida` only because their closure reaches a Lean-generated `T.ctorIdx` (`@[implemented_by T.ctorIdx._impl]`, `CtorIdx.lean:139`). Under Q7, the constant is user-level, because it is in a Mathlib module.
- Mathlib does not write any `implemented_by` in source.
- The most affected areas are `CategoryTheory`, `Algebra` and `AlgebraicGeometry`.
- It is a loss of coverage, not of integrity: none of these declarations comes out `verified`.
- Structural recognition of `ctorIdx` (body `getObjTagNat`, value `casesOn` over the indices) is a Phase 2 item, with an equivalence test on the pinned toolchain.

## L-31. Swapped-statement benchmark (sub-phase 1b)
The false-positive rate on hard correct proofs is 28.6% (target: 10%). Causes: generated ctorIdx (L-34, Phase 2 P0) and backward.* options (roadmap, with a no-effect test). Both are fail-closed — the error is one of coverage, not of integrity. Fixing these two causes is a Phase 2 P0 item and must be measured before any claim of Mathlib coverage to third parties.

**Breakdown of the 10 cases** (instruction 26): 2 only because of a generated `ctorIdx`; 4 only because of `backward.*` (one of them is an anonymous instance, with no binding by design); 4 for both reasons. That is, 8 of the 10 come from two known, fixable causes.

**Detection.** 100 % of the swapped statements, by construction: a false statement with the original proof does not compile. The number that measures the auditor is **11/11 on the cheats that compile**, with the right reason and zero false negatives.

**Measurement:** `docs/benchmark.md`; 5th run, run 39879879325, auditor `81457ac`, official Mathlib `e1b2403b`; 100 valid cases.
- **Cheats that compile** on false statements (`sorry`, `axiom`, `implemented_by` + `native_decide`, `run_tac`, transitive `sorry`): 11/11 detected, right reason 11/11, 0 false negatives.
- **False positives:** 10 of 35 hard correct Mathlib proofs.
  - **Causes:** generated `ctorIdx` (L-34) and `set_option` `backward.*` outside the policy, applied to the theorem itself; an anonymous instance has no binding by design.
  - **Before Stage A v5:** 34.3 %.
- **Controls** (original statements with a simple proof): 0/24 false positives.
- **Sample limits:** the negatives are elementary lemmas (formal ground truth by concrete instance); "hard" is approximated by proof length; 35 theorems from 23 areas.
