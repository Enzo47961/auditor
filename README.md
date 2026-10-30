# auditor — mechanical integrity checker for Lean 4 proofs (Phase 0, Tier 1)

## What this tool does NOT do

Read this section before any other. A seal issued by this tool does **not** mean "the proof is correct" or "the theorem says what its author claims".

> **Mandatory statement (L-26): `classification_review_status: author-self-review`.** The classification of Mathlib commands on which this tool's results rest was written and reviewed by the same author; there has been no independent review. Every report, summary and comment states this. No Mathlib coverage result may be presented to third parties (Mathlib Zulip, paper, blog or elsewhere) without this qualification. Independent review is a Phase 1 item (`docs/roadmap.md`).

*Language note.* Status values that the tool prints, such as `Validada` (validated), `Rejeitada` (rejected), `Não resolvida` (unresolved), `Conforme` (conforming), `Não conforme` (non-conforming) and `Não auditada` (not audited), are quoted below exactly as they appear in the reports.

- **It does not audit correspondence.** It does not check whether the formal statement matches the informal one (paper, LaTeX, the author's intent). Every Phase 0 report states `correspondence_status: "Não auditada"` (not audited), without exception. A theorem that proves the wrong thing gets the same seal as one that proves the right thing.
- **It does not audit the Lean kernel.** The kernel is a trust anchor (TCB), not an audited object. A kernel bug invalidates every seal, and this tool would not detect it.
- **It does not use an LLM**, in any capacity, anywhere in the code.
- **It does no semantic analysis of proofs**: it does not decompose tactics into obligations, does not detect semantic circularity, and does not assess whether hypotheses are vacuous or contradictory.
- **It does not search for counterexamples**, does not try to refute, and does not use SMT.
- **It does not read LaTeX or PDF.**
- **It does not distinguish constructive contexts.** `Classical.choice` is allowed by default; this is an explicit Phase 0 decision, not an omission.
- **It does not act as a bot.** It does not open PRs, does not comment on PRs on its own initiative, and does not act under its own identity. Everything that appears on a PR was requested by a human (see [CI integration](#ci-integration)).
- **It does not revoke seals.** The revocation model is documented in `docs/invalidation.md`; the implementation is Phase 1.
- **It does not guarantee full syntactic coverage in Stage A.** Stage A is a lexical scan, not faithful parsing (see [Limitations](#limitations)). Stage B, which inspects elaborated declarations, is the source of evidence; Stage A only flags candidates.
- **It does not issue a binary verdict.** The output is a map of epistemic debt: three orthogonal states per declaration, plus the list of what was not verified.

## Status

**Phase 0 = closed unconditionally 2026-10-22. Phase 1 = in progress (sub-phase 1a: P0-1 and P0-2; `docs/p0-1-implemented-by.md`, `docs/p0-2-fail-closed.md`).**

Closure confirmed by the project reviewer in instruction 24: auditor `69ed9cf`, fork `auditor-base` `018d7db`, 674 tests, 141/141 mutations, layer-2 steps 8 and 9 (step 9 with a qualified summary), L-26 declared in every artifact. Evidence in `docs/phase0-report.md`. Phase 1 starts with the two P0 items of `docs/roadmap.md`.

The tables below record how the two layers of Phase 0 were built. The go/no-go criterion was layer 2 (GitHub Actions on real PRs in the Mathlib fork), not layer 1.

**Layer 1 — done in the builder's environment.** Items verifiable without Mathlib, with evidence produced in the development environment. Pinned toolchain: **`leanprover/lean4:v4.36.0-rc1`** (Mathlib `master`'s, instruction 12). **Q9 decided (instruction 13):** `native_decide` never comes out `verified` in Phase 0 (permanently fail-closed; re-checking by the kernel is Phase 1 research).

| Item | State |
|---|---|
| README with limitations and a "What it does NOT do" section | under review |
| Conformance suite (5 mandatory scenarios + `04b-extern` + `06-tcb-boundary`) passes | **green** end to end (real CLI, real Lean) |
| Fail-closed suite (3 scenarios) passes | **green**: custom macro and zero-width → `Não resolvida` (Stage A); import cycle → `compile_failure`, exit 1 |
| Stage A (lexical pre-scan) | done: 39 tests, 9 mutations detected; D-1 with `#reduce`/`#guard`/`#widget` |
| Allow-list generator tested against an arbitrary Lake project (Q5) | done: 16 tests, 9 mutations detected |
| Stage B (Lean inspector v2 + wrapper) | done: 13 mutations detected (previous round) |
| TCB boundary (Q7-a) | done: algorithm in `docs/tcb.md`, 19 unit tests, canary `06-tcb-boundary` |
| Policy engine (`policy.toml` + rules with their own regression tests) | done: 30 mutations detected (policy, aggregator, report, boundary, fingerprint) |
| JSON schema v1 published and validated | done: `schema/report-v1.json`; every fixture report validates; the schema rejects 8 violations of principle |
| CLI (`auditor check`) with Q6 exit codes and Q4 `overall_status` | done |
| `docs/tcb.md` | done, with the "TCB boundary" section |
| `docs/invalidation.md` (model only) | done: immutable seals, append-only events, derived state, propagation |
| `docs/limitations.md`, `docs/maintenance.md` | done |
| No LLM dependency (automated check) | done: `tests/maintenance/test_no_llm.py` |
| GitHub Action (reusable workflow + templates for the fork) | done and tested in layer 1: 78 tests (`tests/ci`), `actionlint` clean; actions pinned by SHA, elan by release + SHA-256; PR wall-clock budget with `cache_state`, per-file timeout of 90 s. Testing in a fork is layer 2 |
| Versioned mutation tests (`tools/mutation`) | catalog of 84 mutations in 5 groups, with a catalog-integrity test |
| No unfulfilled promise in the README | pending (final review) |

**Layer 2 — done in the real environment** (evidence in `docs/phase0-report.md`).

| Item | State |
|---|---|
| Mathlib allow-list generated in the fork (`auditor-gen-allowlist --project`), with Mathlib's commands classified | done: 259 commands, 0 unclassified; regenerated in CI byte-for-byte identical (run 39696176700) |
| First run in the fork (cold cache, `first_run: true`) | done: PR #1, 136.1 s |
| Real Mathlib PRs in steady state, with the cache warmed on the base branch (D-61): trivial, medium, fanout on the success path and fanout on the fail-closed path (L-27; ranking from `tools/layer2/fanout.py`), with timings per `cache_state` (`tools/layer2/timings.py`) and `project_dirty: false` (D-62) | done: PRs #5–#8, `warm`, 126–142 s; fail-closed separately (PR #7) |
| Timeout path (`auditor-failed-infra`, without blocking merge) | done: step 8, PR #9 |
| Per-file p95 measured and the per-file timeout default readjusted | **not done**: deferred to Phase 1 (`docs/roadmap.md`, "Measured per-file timeout") |
| GitHub Action integrated and tested in a fork | done: `auditor-tier1`, `auditor-label`, `auditor-report` (step 9, PR #8) and `auditor-warm-cache` in the fork |

**Why two layers.** The development environment has the Lean toolchain (checked: `lean`, `lake` and `#print axioms` work), but has no access to the Mathlib build cache, and building Mathlib from scratch does not fit in it.

**Development environments used.** Linux (sandbox, up to Stage A) and Windows 11 with elan, from Stage B on: `leanprover/lean4:v4.22.0` (commit `ba2cbbf0`) up to instruction 11; **`leanprover/lean4:v4.36.0-rc1`** (commit `c9afcddf`, Mathlib `master`'s toolchain on 2026-10-20) since instruction 12. The whole suite runs on the pinned toolchain.

## Conformance suite: what each scenario tests

| Scenario | Category | Expected state |
|---|---|---|
| `01-sorry-target` | admission in the target file | `Rejeitada` / `Conforme`, `sorryAx_detected` |
| `02-sorry-transitive` | transitive admission (A → B → C → D) | `Rejeitada` / `Conforme`; origin traced to `d_lemma` |
| `03-axiom-unknown` | **unknown** axiom in the premises | `Validada` / `Não resolvido`, `unknown_axiom` |
| `04-implemented-by` | `@[implemented_by]` alone and combined with native evaluation | (a) `Não resolvida`, `implemented_by_candidate`; (b) `Rejeitada`, `implemented_by_reaches_native_eval` |
| `04b-extern` | user-level `@[extern]` alone and combined (O-5); (c) with the toolchain's `Nat.add` in the same statement | (a) `Não resolvida`, `extern_candidate`; (b)/(c) `Rejeitada`, `extern_reaches_native_eval`, only `myF` flagged |
| `06-tcb-boundary` | TCB boundary (Q7-a), canary: `Nat.add` (the toolchain's `@[extern]`) with and without `native_decide`; one probe per root of the roots allow-list (`uses_init`, `uses_lean`, `uses_std`, `uses_lake`; D-42) | no `extern`/`implemented_by` rule fires; without `native_decide`: `verified`; with it: `unresolved` only because of `native_auxiliary_axiom` (Q9-a; on v4.22, `verified`); probes: `verified` |
| `05-native-decide` | **forbidden** mechanism in the premises (native evaluation without justification) and the justification grammar | `Validada` / `Não conforme`; justified: `Validada` / `Não resolvido` (`native_auxiliary_axiom`, Q9-a; on v4.22, `verified`); orphan: `Rejeitada` |

Under strict orthogonality (Q1-X), `sorryAx` is an admission and affects only `proof_status`; that is why the "forbidden in the premises" category is covered by 05, not by 02 (R-1).

## What the tool does

Given a `.lean` file, a pinned environment (`lean-toolchain` + `lake-manifest.json`) and a policy (`policy.toml`), it emits a JSON report (schema v1) with:

- compilation status (success, failure or timeout);
- `sorryAx` and other admissions, including transitive ones;
- the axioms used by each declaration, with transitive dependencies;
- policy violations: an axiom outside the policy, `native_decide` without justification, a suspicious `@[implemented_by]`, a `set_option` that relaxes checking;
- the TCB, enumerated component by component, with versions and hashes;
- an environment fingerprint, for future invalidation;
- `correspondence_status: "Não auditada"` (not audited).

## Architecture

```
file.lean ──► Stage A (lexical parser, Python) ──► candidates ───┐
                                                                  │
lean-toolchain + lake-manifest ──► lake build ──► .olean ──►      │
   Stage B: inspector (Lean metaprogram) ──► raw data ────────────┤
                                                                  ▼
policy.toml ─────────────────────────────────► aggregator (Python)
                                                   │
                                                   ▼
                                    JSON report v1 + seal + exit code
```

The components are separate on purpose: what **reads** the environment is not what **judges**.

**Stage A — lexical parser (Python).** A lexical scan of the target file, without elaboration. It flags `sorry`, `admit`, `axiom`, `native_decide`, `@[implemented_by]`, suspicious `set_option`s, `macro`/`syntax`/`elab`/`notation` declarations in the file itself, commands outside the allow-list and forbidden Unicode characters. **It never issues a positive conclusion.** Its role is to point out candidates and to capture what does not exist in the elaborated environment: `set_option` and comments.

**Stage B — inspector (Lean metaprogram).** Runs after `lake build` in the pinned environment. It imports the compiled modules via `Lean.Environment` and, for each declaration of the target file, extracts the transitive axioms (same algorithm as `#print axioms`), the admissions (`sorryAx`), the use of `Lean.ofReduceBool`/`Lean.ofReduceNat`, the relevant attributes (`@[implemented_by]`, `@[auditor_justified]`) and the metadata for the fingerprint. It produces raw data, without applying policy. The inspector is compiled against the target project's toolchain, because `.olean` files are only readable by the same Lean version; the binary is cached, identified by the hash of source + toolchain, and runs under `lake env` in the target project.

The inspector computes the axioms in two ways: with `Lean.collectAxioms` (the official `#print axioms` algorithm) and with its own dependency closure, which also records who references each axiom, the constants with `@[implemented_by]`/`@[extern]`, and whether each one comes from the toolchain (decided by the `.olean` path, not by the module name). A disagreement between the two, a referenced constant that does not exist (the official algorithm silently ignores it), or an unresolved owner become anomalies, which the aggregator turns into fail-closed.

**Project command allow-list (Q5).** The bundled allow-list covers only the core. For a project with its own commands (Mathlib defines `lemma`, for example), `auditor-gen-allowlist --project <dir>` generates `<dir>/.auditor/allowlist.json`, bound to the environment pin (`lean-toolchain` + `lake-manifest.json`). Stage A uses it only if the pin matches (otherwise `allowlist_stale`, fail-closed). A project command without an explicit classification in `<dir>/.auditor/classification.toml` is fail-closed (`unclassified_command`).

**Aggregator (Python).** Validates the policy, applies the rules to the raw data from Stages A and B, consolidates the three orthogonal states per declaration, assembles the TCB and the fingerprint, validates the report against JSON Schema v1 and sets the exit code.

### Why Python (and not Rust)

The dominant cost of a run is `lake build` (seconds to minutes), not the wrapper's startup (milliseconds). The semantic inspection has to be written in Lean anyway, since only Lean itself reads `Lean.Environment`. The Python wrapper only orchestrates, scans lexically and applies declarative rules. Rust would bring no measurable gain and would slow down iteration.

## Orthogonal states

Each declaration has three independent states, never collapsed into a single verdict.

| State | Values |
|---|---|
| `proof_status` | `Validada` (the kernel accepted it and every mandatory check passed) · `Rejeitada` (a concrete policy violation was demonstrated) · `Não resolvida` (insufficient evidence, timeout, or input outside coverage) |
| `premises_status` | `Conforme` · `Não conforme` (forbidden dependency detected) · `Não resolvido` (incomplete analysis) |
| `correspondence_status` | `Não auditada` — always, in Phase 0 |
| `overall_status` | `verified` · `rejected` · `unresolved`, by the table below (Q4: the worst state wins) |

**`overall_status` (Q4: precedence `rejected` > `unresolved` > `verified`).** It is the safe reading for anyone who reads only this field.

| `proof_status` \ `premises_status` | `Conforme` | `Não conforme` | `Não resolvido` |
|---|---|---|---|
| `Validada` | `verified` | `rejected` | `unresolved` |
| `Rejeitada` | `rejected` | `rejected` | `rejected` |
| `Não resolvida` | `unresolved` | `rejected` | `unresolved` |

Every state other than `Validada`/`Conforme` carries an explicit, machine-readable reason (e.g. `sorryAx_detected`, `unknown_axiom`, `policy_invalid`, `timeout`).

**`Validada` requires, cumulatively:** successful compilation; the inspector finished for the declaration; no admission; a valid policy; a complete TCB; no fail-closed trigger in Stage A or B. If any is missing, the state is `Rejeitada` or `Não resolvida`, never `Validada`. Axioms outside the policy affect only `premises_status`; admissions (`sorryAx`) affect only `proof_status` (strict orthogonality). The consumer reads `overall_status` first; the individual states remain complete in the report.

### The seal

The seal is a string derived from the report, and it always states what was not verified:

```
auditor Tier1 v<version> · Prova: Validada · Premissas: Conforme ·
Correspondência: Não Auditada · Não coberto: correspondência, kernel,
análise semântica, contextos construtivos · fingerprint: <hash>
```

(The seal text is emitted in Portuguese: "Prova" = proof, "Premissas" = premises, "Correspondência" = correspondence, "Não coberto" = not covered: correspondence, kernel, semantic analysis, constructive contexts.)

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Every mandatory check passed for every declaration (`Validada` + `Conforme`) |
| `1` | At least one declaration is not `Validada` + `Conforme`; includes a target that **does not compile** (Q6) |
| `2` | Infrastructure failure: the tool could not run (missing or invalid policy, unpinned or inconsistent environment, timeout, inspector failure); or a file **without declarations** (`no_declarations_found`, D-15): there is nothing to reject, and the user must be explicit (`--allow-empty` for import-only files) |

Unrecognized input **never** results in exit `0`.

**A target that does not compile (Q6)**, including an import cycle: exit `1`, `proof_status: Não resolvida`, `overall_status: unresolved`, reason `compile_failure`. It is a failure of the target detected by the tool: it is not infrastructure (exit 2 is for a tool unable to run) nor a policy violation (`Rejeitada`).

## Policy (`policy.toml`)

The policy is tested code: each rule has its own regression test, and a rule change requires an audit by someone other than the rule's author.

**A missing or malformed policy, or one with a nonexistent rule:** the auditor does not silently apply a default. Every declaration comes out `Não resolvida` / `Não resolvido` with reason `policy_invalid`, exit `2`.

**Axioms.**
- Allowed by default: `Classical.choice`, `propext`, `Quot.sound`.
- Forbidden by default: `sorryAx`; `Lean.ofReduceBool` and `Lean.ofReduceNat` without justification.
- Native-evaluation auxiliary axiom (v4.36+): on `leanprover/lean4:v4.36.0-rc1`, `native_decide` no longer produces `Lean.ofReduceBool`: it adds, per use, an auxiliary axiom `<owner>._native.native_decide.ax_N : e = true` (`Lean.Meta.nativeEqTrue`), which the kernel does not re-check. The inspector recognizes it by its shape (`native_auxiliary`); the policy treats it as native evaluation for the justification rules and for the combined pattern, and **additionally** leaves the premises `Não resolvido` (`native_auxiliary_axiom`), because the shape does not prove the origin. Decision Q9 (option a): permanent in Phase 0.
- An axiom on neither list: governed by `unknown_axiom_action`, default `fail_closed` (state `Não resolvido`, reason `unknown_axiom`, with a suggested policy update). The alternative value `allow_with_warning` requires a written justification in the policy itself and a regression test.

**`native_decide`.** Blocked by default. Allowed only with a justification in the docstring of the owning declaration, on a single line with a strict grammar:

```lean
/-- Free docstring text.
auditor_justified: reason="motivo" reviewer="@handle" -/
theorem t : 10 < 20 := by native_decide
```

Stage B reads the docstring from the elaborated environment (`.olean`) and associates the justification by declaration name, not by position in the file. There is no escaping, no multi-line continuation and no duplicate; any deviation is a violation (`native_decide_justification_malformed`). A justification on a neighbouring declaration does not cover the one that uses `native_decide`. Declarations that inherit `Lean.ofReduceBool` transitively are traced back to the owning declaration. No dependency in the target project is needed. Approval is human and out of scope. Details and residual risks in `docs/limitations.md` (L-4).

**`@[implemented_by]`.**
- Alone, it does not affect the kernel: `Não resolvida`, reason `implemented_by_candidate`.
- Combined: if the declaration's transitive axioms include `Lean.ofReduceBool` or `Lean.ofReduceNat` **and** the declaration's dependency closure contains a constant with `@[implemented_by]`, the state is `Rejeitada`, reason `implemented_by_reaches_native_eval`. A `native_decide` justification does **not** cover this case. The pattern is written in the policy and has its own regression test.

**`@[extern]` (O-5).** Same risk category as `@[implemented_by]`: it replaces the compiled implementation, and `native_decide` trusts it. Analogous rules (alone: candidate; combined with `Lean.ofReduceBool`/`Lean.ofReduceNat`: `Rejeitada`), with its own scenario (`04b-extern`, ground truth: derives `False`).

**TCB boundary (Q7, option a).** The `@[implemented_by]` and `@[extern]` rules apply only to **user-level** declarations. The toolchain's own implementations (`Nat.add`, `Lean.Name.str`, …) are TCB and trigger nothing. The boundary is declared by the toolchain (library roots in `<sysroot>/lib/lean`) and by `lake-manifest.json` (user packages), never by the module name. Whatever cannot be decided is `Não resolvida` (`tcb_boundary_unresolved`). Algorithm and maintenance in `docs/tcb.md`; the canary is scenario `06-tcb-boundary`.

**`set_option`.** Versioned allow-list. `maxHeartbeats 0` is **always** a violation under the default policy, on any path. A custom policy may exempt it, but only under two cumulative conditions: (a) the file is on an explicit allow-list of paths; and (b) the option is in the form `set_option maxHeartbeats 0 in` applied to a declaration whose docstring has `auditor_justified: reason="test-only heartbeat exemption" reviewer="@handle"`. `set_option maxHeartbeats 0` at file or section level is never exemptable.

**Scope of a `maxHeartbeats 0` violation:** it invalidates **only the declaration that uses it** (the `in` form). The other declarations of the file are evaluated normally and pass if they do not depend on it. A declaration that **depends** on the violating one keeps its own state (it may be `Validada` + `Conforme`); the dependency is visible in the `depends_on_rejected` field. At file or section level, the option affects every declaration in its scope, and each is flagged individually. `autoImplicit true` and `checkBinderAnnotations false` are violations by default.

## Unicode

Versioned allow-list, aligned with Unicode TR36/TR39.

- **Bidirectional controls and zero-width characters**, in any position (including comments and strings): fail-closed. This is a real security risk (Trojan Source).
- **Confusables** (for example, Cyrillic letters that imitate Latin ones): a warning in the report, not a failure. The kernel is not confused; the risk is to the human reviewer.
- Usual mathematical Unicode (`ℝ`, `∀`, `∑`, …) is allowed.

## Environment fingerprint

A hash that captures:

- the exact `lean-toolchain` version;
- the Mathlib commit and the hash of `lake-manifest.json`;
- the inspector's hash (source and compiled binary);
- the aggregator's version and source hash, and the Python interpreter version;
- the version of the Stage A parser and of the allow-list;
- the policy's version and hash;
- the hash of the transitively imported metadata: all `@[simp]`, `@[ext]`, `@[reducible]` and `@[implemented_by]`.

A change in any component invalidates the seals issued against the previous fingerprint. Phase 0 does not do this automatically: the report states the fingerprint, and the consumer compares it with the current environment.

## TCB (Trusted Computing Base)

Every report enumerates the TCB against which the seal was issued. At minimum:

| Component | Identification in the report |
|---|---|
| Lean kernel | toolchain version + commit |
| Toolchain (elaborator, `lake`) | exact `lean-toolchain` |
| Mathlib and other dependencies | commit + hash of `lake-manifest.json` |
| Inspector (Lean metaprogram) | hash |
| Aggregator (Python) | version + hash + interpreter version + transitive Python dependencies with exact versions (`jsonschema` and what it pulls in; D-20) |
| Stage A parser | version + allow-list version |
| Policy | version + hash |

An incomplete TCB prevents `Validada`. Details in `docs/tcb.md`.

## Usage

```
auditor check <file.lean> --output report.json --policy policy.toml
        [--timeout-file 90] [--timeout-test artificial] [--allowlist <allowlist.json>]
```

Requirements: Python ≥ 3.11 with `jsonschema` (`pip install -e .`), and `elan` on the `PATH` with the target project's toolchain. The file must be in a Lake project with `lean-toolchain` and `lake-manifest.json`. The first run with a new toolchain compiles the inspector (about 15 s); later runs reuse the cached binary.

For projects with their own commands (Mathlib), first generate the project allow-list: `auditor-gen-allowlist --project <root>` (see `docs/maintenance.md`).

The report is validated against `schema/report-v1.json` before it is written. Each declaration carries `seal`, the seal string, which always states what was not verified.

The environment comes from the `lean-toolchain` and `lake-manifest.json` of the project containing the file. No Lean, Mathlib or policy version is hard-coded in the tool.

## CI integration

GitHub Action `auditor-tier1` (reusable workflow `.github/workflows/auditor-tier1.yml` + templates in `ci/templates/` for the target repository; details and installation in the fork in `docs/ci.md`):

- runs on PRs that touch `.lean` files, triggered by the repository's workflow, under the repository's identity; the job that compiles the PR's code has read-only permission (the label is applied by a separate workflow that never runs PR code);
- publishes the summary in the run's **Job Summary** and attaches the full JSON report as an artifact;
- **does not comment on the PR automatically.** A comment with the summary is posted only when a human explicitly asks for it on the PR (`@auditor report`);
- **5-minute PR wall-clock budget**, from trigger to report, including `lake exe cache get` (steady state). If it does not finish: exit 2, label `auditor-failed-infra`, it **does not block the merge**, and it requires explicit human review. A timeout is never treated as success;
- **per-file timeout of 90 s**: a file that exceeds it ends the PR's audit (exit 2);
- the report states `cache_state` (`cold`, `delta`, `warm`). With a cold cache (first run), the budget is extended (15 min), the result states `first_run: true`, and exceeding 5 min is not a failure: `cache_cold_extension` and label `auditor-first-run`;
- every action is pinned by commit SHA.

## Limitations

- **Stage A is not faithful parsing.** Lean's syntax is extensible: the parser depends on imported notations. Stage A does a lexical scan and detects macros and notations declared in the file itself; notation coming from imports is only covered by Stage B. The allow-list is versioned per toolchain, and a test fails if it falls out of date relative to the pinned `lean-toolchain` (see `docs/maintenance.md`).
- **`set_option` and comments exist only in Stage A**, because they are not recorded in the elaborated environment.
- **A fingerprint is not revocation.** Detecting that a seal has become stale is the consumer's responsibility in Phase 0.
- **`Classical.choice` is allowed by default.** Constructive contexts are a Phase 3+ topic.
- Full list in `docs/limitations.md`.

## Principles

1. **Error asymmetry.** A false "verified" is catastrophic; "unresolved" for a correct proof is only an inconvenience.
2. **TCB enumerated per seal.**
3. **Fail-closed.** Unrecognized input produces an explicit failure with a reason, never a positive seal.
4. **No LLM on the critical path.**
5. **Independent ground truth.** Negative tests use a verifiable counterexample or a proof of the negation in Lean.
6. **The seal states what was not verified.**
7. **Expiry bound to the fingerprint.**
8. **No autonomous bot.**

## Documentation

- `docs/tcb.md` — full TCB manifest
- `docs/invalidation.md` — data model for seals and revocation (implementation in Phase 1)
- `docs/limitations.md` — detailed limitations
- `docs/maintenance.md` — maintenance of the allow-list, the inspector, the mutation tests and workflow version pinning
- `docs/ci.md` — CI integration, workflow security, installation in the fork and the layer-2 evidence plan (tools in `tools/layer2/`)
- `docs/roadmap.md` — decided Phase 1 and Phase 2 items
- `docs/layer2-checklist.md` — layer-2 step by step (commands, checks, abort criteria, report format), for the maintainer to execute
- `docs/user-study.md` — methodology and pre-registered metrics of the user study (sub-phase 1c)
- `docs/benchmark.md` — the swapped-statement benchmark (sub-phase 1b)
- `CHANGELOG.md` — changes that affect auditor users
- `docs/proposed-improvements.md` — recorded objections to the specification
