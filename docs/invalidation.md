# Seal invalidation — data model

**State: model only.** In Phase 0, nothing in this document is implemented beyond what the report already emits: a fingerprint and the TCB per declaration. Seal storage, the event log, propagation and signing belong to Phase 1. This document fixes the model so that Phase 1 does not need to reinterpret the v1 report.

## Principles

1. **Seals are immutable.** A seal is never edited or deleted. A seal's current situation is **derived**: seal + event log + the consumer's environment.
2. **Revocation is an event, not an edit.** Events are appended to an *append-only* log; no event is removed. An event issued by mistake is neutralized by another event (`retraction`), which also stays in the log.
3. **Stale is not revoked.** A seal issued against another environment (a fingerprint different from the current one) is **stale**: it does not apply to the consumer's environment, but it has not been refuted either. A **revoked** seal was declared invalid by an event. The two situations are never confused.
4. **When in doubt, it does not hold.** If the consumer cannot decide a seal's state (inaccessible log, malformed event, missing fingerprint), the state is `undetermined`, never `valid` (fail-closed, principle 3).
5. **Human in the loop.** Revocation events are created by identified people (principle 8). The tool may **detect** environment changes, but it does not issue revocations on its own.

## Entities

### Seal (`Seal`), immutable

Derived from an entry of a v1 report's `declarations`. All fields already exist in the report (the source field in parentheses).

| Field | Source in the v1 report | Note |
|---|---|---|
| `seal_id` | — | SHA-256 of the canonical form (JSON, sorted keys) of the fields below, except `issued_at` and `report_sha256` |
| `declaration_name` | `declaration_name` | |
| `declaration_hash` | `declaration_hash` | identity of the elaborated content (D-18) |
| `module` | `target.module` | |
| `proof_status`, `premises_status`, `overall_status` | same | the seal records the result, including negative ones |
| `correspondence_status` | same | always `Não auditada` (not audited) in Phase 0 |
| `fingerprint` | `tcb.fingerprint` | the environment against which the seal holds |
| `tcb` | `tcb` | enumerated components (kernel, toolchain, dependencies, inspector, aggregator, parser, policy, metadata) |
| `depends_on_rejected` | same | |
| `local_dependencies` | (Phase 1: the inspector's complete `depends_on`) | declarations of the same module in the closure; dependencies in other modules are covered by the fingerprint (imports pinned by the manifest) |
| `issued_at` | `execution_metadata.timestamp` | |
| `report_sha256` | — | hash of the report the seal was extracted from (traceability) |

A seal with `fingerprint: null` (incomplete TCB) cannot be stored as a seal: the report already guarantees that such a declaration is not `Validada`.

### Event (`Event`), append-only

| Field | Type | Note |
|---|---|---|
| `event_id` | SHA-256 of the canonical form of the event without `event_id` | |
| `kind` | enum, below | |
| `selector` | object, below | **which** seals the event affects |
| `reason` | text | mandatory |
| `evidence` | list of references (URL, commit, issue, report) | mandatory for `revocation` |
| `author` | human identity | principle 8; never an automation account |
| `created_at` | timestamp | |
| `supersedes` | `event_id` or null | only for `retraction` |

**Kinds (`kind`):**

| `kind` | Effect on the selected seals | Example |
|---|---|---|
| `revocation` | `revoked` | a bug in kernel 4.36.0-rc1; a defect in inspector v2 that omitted axioms; policy v1 had a wrong rule |
| `retraction` | cancels the effect of an earlier event (`supersedes`) | a revocation issued for the wrong version |
| `advisory` | no effect on the state; the notice is shown to the consumer | a policy rule reconsidered, with no demonstrated error |

**Selector (`selector`):** a conjunction of conditions on seal fields. Examples:
- `{"tcb.kernel.lean_version": "4.36.0-rc1"}`
- `{"tcb.inspector.source_sha256": "sha256:…"}`
- `{"tcb.policy.sha256": "sha256:…", "declaration_name": "foo"}`
- `{"fingerprint": "sha256:…"}`

An empty selector is invalid (there is no revocation of "everything" by omission).

## Derived state of a seal

Input: the seal `S`, the log `L` and the fingerprint `F` of the consumer's current environment (computed by the same function as `src/auditor/fingerprint`).

1. If `L` could not be read or contains a malformed event → `undetermined`.
2. Remove from `L` the events cancelled by valid `retraction`s.
3. If any remaining `revocation` selects `S` → `revoked`.
4. If any seal **that `S` depends on** is `revoked` (propagation, below) → `revoked` (cause: `propagated`, with the path).
5. If `S.fingerprint ≠ F` → `stale`.
6. If `S.overall_status ≠ verified` → `negative` (the seal records a rejection or non-resolution; it remains immutable and queryable).
7. Otherwise → `valid`.

The order matters: revocation prevails over staleness. A revoked seal remains revoked even when the environment changes.

## Propagation

Revoking a seal may invalidate others that depend on it.

- **Same module:** if `S` lists `T` in `local_dependencies` and `T` is revoked, then `S` is revoked (transitively, up to a fixed point).
- **Other modules:** there is no explicit edge. An imported dependency is pinned by the manifest and the commits, which enter the fingerprint. Revoking something in a dependency is expressed by a selector on the fingerprint's components (for example, `tcb.dependencies.mathlib_commit`), not by edges between seals. This keeps the model from depending on a global declaration graph that Phase 0 does not build.
- **TCB components:** revoking a component (kernel, inspector, aggregator, policy) is a selector on `tcb.*`, which directly hits every seal issued with it. No propagation is needed.
- **Cycles:** Lean's dependency closure is acyclic for elaborated declarations; propagation iterates to a fixed point and terminates.

## What Phase 0 already guarantees

- The report declares `fingerprint` and the complete TCB in each declaration; `Validada` requires a complete TCB (schema v1).
- `declaration_hash`, `depends_on_rejected` and the orthogonal states have the fields needed to extract seals without reinterpretation.
- Comparing the fingerprint with the current environment is the consumer's responsibility (L-10).

## Outside the model (Phase 1+)

- Cryptographic signing of seals and events, and verifiable author identity.
- Where the log is stored and how it is distributed.
- A complete `local_dependencies` in the report (today only `depends_on_rejected` is emitted).
- Automatic revocation from detected environment changes. This is not planned: detection is automatic, but revocation is human.
