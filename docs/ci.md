# CI integration (GitHub Actions)

## Pieces

| File | Where it lives | Trigger | Permissions | Runs PR code? |
|---|---|---|---|---|
| `.github/workflows/ci.yml` | this repository | push, PR | read | — (tests the auditor itself) |
| `.github/workflows/auditor-tier1.yml` | this repository (reusable) | `workflow_call` | **read** | **yes** (`lake build`) |
| `ci/templates/auditor-tier1.yml` | target repository | `pull_request` on `**.lean` | read | yes, through the reusable one |
| `ci/templates/auditor-label.yml` | target repository | `workflow_run` (auditor-tier1 completed) | write on PRs/issues | **no** |
| `ci/templates/auditor-report.yml` | target repository | `issue_comment` (`@auditor report`) | write on PRs | **no** |

The logic lives in `auditor-ci` (`src/auditor/ci.py`), tested in `tests/ci`. The workflows only call it. The workflows' security policy is also a test (`tests/ci/test_workflows.py`): no `pull_request_target`, minimal permissions, no checkout in workflows with write access, no interpolation of PR text into scripts, actions pinned by commit SHA, elan from a pinned release with a checked SHA-256. All 5 files pass `actionlint` 1.7.12.

"Instruction N" refers to the numbered decisions of the project's external reviewer.

## Behaviour (spec, component 7; instruction 11)

- **Runs on every PR that touches `.lean`**: the template filters by `paths: ["**.lean"]`, and the job audits the `.lean` files changed between base and head that still exist.
- **PR budget = wall clock from the trigger to the report (D-28).** The clock starts at the PR event (`github.event.pull_request.updated_at`; on a re-run, at the start of the job) and **includes preparation**: installation, `lake exe cache get` and compiling the inspector. `outcome.json` declares `clock_origin`, `setup_elapsed_s`, `audit_elapsed_s` and `elapsed_s`.
  - **Steady state (`cache_state` `warm` or `delta`): 5 min** (`timeout-total-seconds`; `auditor-ci run --timeout-total`; default 300).
  - **`cold` cache: extended budget** (`timeout-total-first-run-seconds`; `--timeout-total-first-run`; default 900) and `first_run: true`. If the audit goes past 5 min without exceeding the extended budget, the PR **does not fail**: `cache_cold_extension: true` and the `auditor-first-run` label (different from `auditor-failed-infra`). The 5-min SLA is declared as steady state.
- **`cache_state`** comes from two measured signals, never from assumption:
  - the target's build cache (`~/.cache/mathlib`, restored by `actions/cache/restore`): `hit` (exact key: same base commit), `partial` (only `restore-keys`), `miss`, or `none` (a target without `cache-get`);
  - the inspector binary in the local cache (`hit`/`miss`, measured by `auditor-ci`).
  - Rule: `cold` if the build cache is `miss` or the inspector is `miss`; `delta` if the build cache is `partial`; otherwise `warm`. **The extended budget is only granted with positive evidence of a cold cache**: a missing signal counts as warm.
- **Per-file timeout (D-21): 90 s** (`timeout-file-seconds`; `auditor check --timeout-file`). Each file gets the smaller of the per-file timeout and what remains of the budget. A file that exceeds the timeout **ends the PR's audit**: the following files are `not_audited_after_timeout` and the PR exits with **exit 2**. A file that no longer fits in the budget is `skipped_budget`. The inspector is compiled before the first file, so as not to consume one file's timeout.
- **PR exit code** (`auditor-ci run`, same codes as the CLI): 0 everything verified; 1 rejection or non-resolution; 2 infrastructure (budget, timeout, exit 2 from some file). Infrastructure wins: a PR with one rejection and one timeout exits with 2, and `audit_failed` remains `true`.
- **Result on GitHub:**
  - infrastructure (exit 2, unreadable report, job cancelled or without a result): the job **does not fail because of it**, so it does not block merging; the label workflow applies `auditor-failed-infra`, which requires explicit human review; a timeout is never success;
  - rejection or non-resolution (`audit_failed`): a dedicated step fails the job. Whether the check is required is a setting of the target repository (D-22).
- **Summary** in the Job Summary, with the notice "Correspondência: Não Auditada" (correspondence: not audited), `cache_state`, timings (preparation, audit, total) and per-file p95. **Full reports** in the `auditor-report` artifact, together with `outcome.json` (format `auditor-ci-outcome/2`) and `summary.md`.
- **A comment on the PR only on human request:** a comment whose first line starts with `@auditor report`, from an OWNER, MEMBER or COLLABORATOR, publishes the summary of the latest run for the current commit. The system never comments on its own initiative.

### Human-triggered flow (`@auditor report`, layer-2 step 9)

1. A human with access to the repository comments `@auditor report` on the PR. The comment stays on the PR under their account: the request is identified as the human's, not a bot's.
2. `auditor-report` is triggered by `issue_comment`. The job's condition requires a PR, a first line starting with `@auditor report`, and `author_association` in OWNER, MEMBER or COLLABORATOR. Any other comment creates no job.
3. The job does not check out and does not run PR code. It installs the auditor at the pinned SHA and reads the PR's `headRefOid` (checked as 40 hex characters).
4. It finds the `auditor-tier1` run for that commit by listing the workflow's 100 most recent runs and selecting by `head_sha` on the client. The API's `head_sha` filter (the one `gh run list --commit` uses) is not deterministic (step 9, instruction 22).
5. It answers with **one** comment, signed by `github-actions`:
   - run found and completed: the summary (`auditor-ci comment`), starting with "Pedido por um humano" (requested by a human). The summary carries at the top the line `classificação: <classification_review_status> (L-26)` (for example, `author-self-review`), taken from the reports; the Job Summary carries the same line;
   - run in progress: a notice to ask again when it finishes;
   - run completed without the `auditor-report` artifact: an infrastructure failure;
   - no run among the 100 most recent: a notice with the commit.
6. The full report remains only in the `auditor-report` artifact of the `auditor-tier1` run. The comment is the summary.
- **Inspector cache (D-7):** `actions/cache` in `~/.cache/auditor`, keyed by the auditor ref + `lean-toolchain`. The Job Summary records, per file, whether the binary was cached (`hit`/`miss`).
- **Version pinning (D-25, mandatory):** every action by commit SHA, with the version in a comment; elan downloaded from release `v4.2.4` and checked by SHA-256. `elan-init.sh` is not used: even taken from a tag, it downloads elan's `latest` release. Update procedure in `docs/maintenance.md`.

### Why three workflows (D-24)

Mathlib PRs often come from forks. The job that audits must compile the PR's code (`lake build`), and untrusted code **never** runs with a write token (the `pull_request_target` + PR checkout pattern is a known vulnerability). Therefore:
- the audit runs on `pull_request`, with a read-only token, and neither applies labels nor comments;
- the label is applied by `workflow_run`, which runs in the repository's trusted context, never checks out, and treats the audited job's artifact as untrusted data (`auditor-ci label-decision` reads only the booleans `infra_failed` and `cache_cold_extension`, with strict type checking; any deviation results in `auditor-failed-infra`, fail-closed);
- the comment is triggered by `issue_comment`, also without checkout.

## Installation in the Mathlib fork (layer 2)

1. Pin the auditor to a commit: `AUDITOR_SHA`.
   - **Toolchain:** the auditor ships a core allow-list only for the pinned toolchain (`src/auditor/data/allowlist/`; today, `leanprover/lean4:v4.36.0-rc1`, Mathlib `master`'s at commit `e1b2403b`). The base of the measurement PRs must use this toolchain. If Mathlib bumps its version before the measurement, there are two ways out: pin the fork to commit `e1b2403b` (or another with the same `lean-toolchain`), or bump the auditor's toolchain again (`docs/maintenance.md`). With another toolchain, every file comes out `allowlist_unavailable` (fail-closed).
2. Copy `ci/templates/*.yml` into the fork's `.github/workflows/` and replace `OWNER/auditor` and `AUDITOR_SHA`.
3. Generate and version the Mathlib allow-list: `auditor-gen-allowlist --project .` after `lake exe cache get`, and classify the commands in `.auditor/classification.toml` (see `docs/maintenance.md`). Without it, every Mathlib file comes out `Não resolvida` (unresolved) because of `unknown_command`.
4. Do the **first run** (cold cache): any PR that touches a `.lean` file. It declares `first_run: true`. It is not a steady-state measurement. The caches it saves only work for itself: the GitHub Actions cache is isolated per ref, and a PR only reads its own ref's cache or the base branch's.
5. **Warm the cache on the base branch (D-61):** the `auditor-warm-cache` workflow runs on every push to the base and on `workflow_dispatch`. It saves, on the base's ref, the inspector and Mathlib caches with the same keys as `auditor-tier1`. Run it again whenever `AUDITOR_SHA` changes, because the inspector key includes the SHA.
6. Open the measurement PRs **after** warming. Expected: `cache_state: warm`, `build_cache: hit` and `inspector: hit` from the first push.

## Choosing the highest-fanout file (D-38)

`tools/layer2/fanout.py <project> --root Mathlib` ranks the project's modules by fanout.

**(a) How it is computed.**
1. It lists the `.lean` files under `<project>/<root>/` and `<project>/<root>.lean`; the module name is the relative path with `/` → `.`.
2. It reads only the **header** of each file: blank lines, line comments (`--`) and block comments (`/- … -/`, with nesting), `prelude`, `module` and `import` lines (with the modifiers `public`, `meta`, `private`; several modules per line). The first command of another kind ends the header, as in Lean. An unreadable module name (e.g. with `«»`) or a block comment inside an `import` line is an error (exit 2), never ignored.
3. It builds the import graph **restricted to the project**: imports from outside (`Init`, `Std`, `Lean`, dependencies) are dropped.
4. It reverses the edges and computes, by breadth-first search, for each module:
   - `direct`: how many modules import it directly;
   - `transitive`: how many modules depend on it directly or transitively (reverse closure);
   - `imports_transitive`: how many project modules it itself imports, directly or transitively (forward closure).
5. It sorts by `transitive` descending, then `direct` descending, then name. Deterministic.

There is no weighting by use: an edge is an `import`, not a reference to a constant.

**(b) Why this definition.**
- Transitive reverse fanout is the measure of "invalidation radius": changing the module invalidates the `.olean` of all dependents. In Mathlib, this decides how much of the `lake exe cache get` cache stops matching the PR's commit. Whether this weighs on time is a **hypothesis to measure**, not a fact: the target module's `lake build` only needs the modules it imports, not its dependents; the expected effect is on preparation (`cache get`), which the 5-min budget now includes (D-28).
- Restricting to the project and using only the header makes the tool cheap (it needs to compile nothing and load no `.olean`) and reproducible from the checkout.
- Weighting by use (counting references to constants) would require the elaborated environment of all of Mathlib and would measure something else: how much the proofs depend on the module, not how much of the build is invalidated. It is left out.
- **Caveat, so that the measurement is not misread:** the cost of **auditing** a file (the target module's `lake build` and the inspector's reading of the environment) grows with the **forward** closure (`imports_transitive`), not with fanout. A maximum-fanout file tends to sit at the base of the hierarchy, with a small forward closure. That is why the tool also prints `imports_transitive`; the "medium" file or a fourth PR can be chosen by the largest forward closure, if the reviewer wants to measure the worst case of the audit itself.

**(c) How it is tested** (`tests/maintenance/test_layer2_tools.py`):
- header: nested comments, `module`, `public import`, several modules per line, an end-of-line comment, stopping at the first command (an `import` after a `theorem` does not count);
- unreadable name → error;
- a synthetic graph of 5 modules with a transitive dependency, a dropped external import and a root module: exact values of `direct`, `transitive` and `imports_transitive`, and the ranking order;
- provenance and `--expect-commit`: a commit different from the expected one → exit 2, no ranking.

**(d) Reproducibility: the choice does not depend on the day's `master`** (instruction 13).
- The tool does not access the network or `master`: it only reads the checkout passed as an argument. The
  result is a function of the checkout's commit, and only of it.
- The JSON output records provenance: the checkout's commit (`git rev-parse HEAD`), the SHA-256 of
  `lake-manifest.json` and the `lean-toolchain`. The graph only has project modules, so the
  manifest's dependencies do not change the ranking. The manifest hash is recorded to prove
  that the checkout is the pinned one, not because the ranking depends on it.
- `--expect-commit <sha>`: if the checkout is not at that commit, the tool exits with 2 and does not
  print the ranking. The layer-2 checklist (step 6) passes `e1b2403bdd31…`.
- There is no "D-38 drift test" against the real Mathlib in the suite: the suite does not download
  Mathlib. The guarantee is this provenance, checked at measurement time. The suite's test covers
  the mechanism (synthetic graph and commit check).

## Pending evidence (layer 2): plan

Phase 0 only closes with this evidence. Phase 1 does not start before it.

| DoD item | How to produce it |
|---|---|
| First run in the fork | any PR; record `cache_state` (`cold` expected), `first_run`, `elapsed_s` and whether there was a `cache_cold_extension` |
| Measurement PRs in steady state (cache warmed on the base, D-61) | **trivial** (e.g. a docstring in a leaf file), **medium** (a new lemma in a typically sized file), **fanout, success path**: the highest-fanout file among those that do not declare syntax (L-27), with the probe `verified`; **fanout, fail-closed path**: the highest-fanout file, if it declares syntax, measured separately and with the probe `unresolved` as the expected result. The ranking comes from `python tools/layer2/fanout.py <fork> --root Mathlib --expect-commit <base>` (attach the table; the old `Mathlib/Logic/Basic.lean` does not exist at the pinned commit: it is `Mathlib/Basic/Logic/Basic.lean`) |
| Timings per `cache_state` | download the `auditor-report` artifact of each run and run `python tools/layer2/timings.py <directories>`: total, preparation, audit and per-file p95, split by `cold`/`delta`/`warm` |
| Timeout path (`auditor-failed-infra`, non-blocking) | a PR with a small artificial `timeout-file-seconds` (e.g. 5): the PR exits with exit 2, the job stays green and the PR gets the label |
| Action integrated and tested in a fork | the items above + an `@auditor report` from a collaborator |
| Readjusting the per-file timeout | per-file p95 measured; the 90 s default is readjusted with data, not intuition |
| Premise checks | the event's `updated_at` timestamp matches the push (compare with the commit time); the size of `~/.cache/mathlib` fits in the repository's cache limit |

Bring: the 3 reports (`outcome.json` + `summary.md`), the `timings.py` table and the `fanout.py` table.

The timeout/label/non-blocking/first-run behaviour is already tested in layer 1 (`tests/ci/test_ci.py`), with artificial timings.
