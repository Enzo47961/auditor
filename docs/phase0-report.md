# Phase 0 report

```
phase_0_status: "closed unconditionally at 2026-10-22, auditor 69ed9cf, fork auditor-base 018d7db, 674 tests, 141/141 mutations, step 8 + step 9 qualified, L-26 declared in all artifacts"
```

**Unconditional closure confirmed by the project reviewer in instruction 24 (2026-10-22).** The evidence for the four accepted criteria is in the final section, "Evidence for the unconditional closure". Earlier status, kept as history: `"closed at layer 1 + layer 2 measurement, pending steps 8-9"` (instruction 22).

"Instruction N" refers to the numbered decisions of the project's external reviewer.

**Phase 1: authorized by the reviewer (instruction 24), not yet started at the time of this report; it starts with the two P0 items of `roadmap.md`.**

**Note (Phase 1, instruction 24) — L-17 was incomplete.** L-17 was incomplete; Phase 1 discovered that tactics and terms (run_tac, by_elab) execute code without detection. L-17 was amended in Phase 1. The Phase 0 results remain valid because the measured PRs did not use these mechanisms. Details: L-33 and L-33a in `limitations.md`; inventory in `docs/l33-inventory.md`.

Closure declared by the reviewer in instruction 22 (2026-10-22), with two conditions before Phase 1 opens:

1. steps 8 (timeout / `auditor-failed-infra`) and 9 (`@auditor report` on human request) of `docs/layer2-checklist.md`;
2. the pending item from the discarded external review closed: answered, or declared unanswered (`proposed-improvements.md`).

After steps 8 and 9, the reviewer confirms the unconditional closure.

**Mandatory statement (L-26).** The classification of Mathlib commands on which these results rest was written and reviewed by the same author. Every report of this phase declares `classification_review_status: author-self-review`. Any external presentation of these results (Mathlib Zulip, paper, blog post or elsewhere) must state that the classification is self-reviewed. Phase 1 includes an independent review before any claim of Mathlib coverage in an external context.

## Context

| Item | Value |
|---|---|
| Auditor run | `7f7238d69adcd3255e3693ddbe76a2cf3302dff4` (only documentation changed after it) |
| Measurement fork | `Enzo47961/mathlib4`, `auditor-base` = `2efeeec` = Mathlib `e1b2403b` + only `.github/` and `.auditor/` |
| Toolchain | `leanprover/lean4:v4.36.0-rc1` |
| Runner | `ubuntu-24.04` (D-55) |

## Closure criteria

| Criterion | State | Evidence |
|---|---|---|
| 3 `warm` PRs under 5 min on the success path (trivial, medium, fanout) | met | #5 126.1 s · #6 129.7 s · #8 137.6 s |
| Fanout probe on the success path `verified` | met | PR #8: `auditor_probe_fanout_success` `verified`, 9/9 in the file |
| Fail-closed path reported separately | met | PR #7 (`Data/Set/Defs.lean`) |
| Every report with `author-self-review` | met | PRs #5–#8 and the `auditor-prep` smoke test |
| Every report with `project_dirty: false` | met | PRs #5–#8 and the `auditor-prep` smoke test (D-62) |
| L-27 amended ("clean Stage A") | met | `docs/limitations.md` |
| Clarification of PR #6 | met: (a) | a wording error in the instruction-20 report; no bug in Stage A |
| Step 8 (timeout / `auditor-failed-infra`) | executed, passed | PR #9: `timeout_kind: file`, exit 2, `infra_failed: true`, green job, PR mergeable, label `auditor-failed-infra`, no comment |
| Step 9 (`@auditor report` on human request) | executed; 1st attempt failed (bug fixed), 2nd passed | PR #8: one "Pedido por um humano" (requested by a human) comment, correct summary (`maintenance.md`) |
| Pending item from the discarded external review | answered | another AI without access to the source code (`proposed-improvements.md`) |

## Conditions

- **Step 8.** PR #9 (`l2-timeout-w`, `timeout-file-seconds: 5`, never for merge), run 39818035267: `Hydra.lean` `timeout` at 5.54 s, `exit_code: 2`, `infra_failed: true`, `cache_state: warm`, green job, `mergeable`, label `auditor-failed-infra`. Reference test in `maintenance.md`.
- **Step 9.** The 1st attempt (run 39818084000) answered "no run" for an audited commit: the `head_sha` filter of GitHub's API is not deterministic. Fixed in the `auditor-report.yml` template (auditor `7ba9b6f`, fork `465d97e`); the 2nd attempt (run 39821013448) posted a single correct comment. Not tested: a comment from someone without access (it would require another account); the guarantee is the `author_association` condition, locked by a test.
- **External review.** Another AI, without access to the source code; diagnosis and rules for Phase 1's independent review in `proposed-improvements.md`.
- **Validation after the fix:** suite 666 passed (`7ba9b6f`); mutation 138/138.

## Records from instruction 23

- **L-29.** "Step 9 tested the @auditor report flow triggered by an OWNER. It did not test the path of a comment from someone without access — the guarantee is the author_association condition, locked by a unit test, not tested end to end in layer 2. An end-to-end test requires a second account; it remains an information gap, non-blocking." (`docs/limitations.md`).
- **Non-determinism of GitHub's API.** The `head_sha` filter of the runs API alternates between 0 and 1 result for the same query, on all three endpoints. It was the cause of step 9's first failure. Evidence and workaround in `proposed-improvements.md`, "Known GitHub API quirks".
- **Discarded external review.** The maintainer's answer: another AI, without access to the source code. This matches the line shift (+16 to +25) of the 4 citations. The rules for Phase 1's independent review were approved and are in `roadmap.md`.
- **Qualification in the summary.** The line `classificação: … (L-26)` goes into the Job Summary and into the `@auditor report` comment before the unconditional closure. Evidence (auditor `69ed9cf`, fork `018d7db`):
  - step 9 re-run on PR #8: a new audit (run 39826300196, `warm`, 135.6 s, 9/9 `verified`, `classification_review_status: author-self-review` in `outcome.json`); a single comment (run 39827471933) with `classificação: author-self-review (L-26)`;
  - suite 674 passed, 0 failed (run 39825726718);
  - `ci` mutation 38/38, including the mutant that removes the summary line (run 39826324751); state 141/141;
  - `auditor-prep` green (run 39826330043): 259 commands, 0 unclassified, `gen_tcb_roots --check` exit 0, smoke test 20/20 with the line in the summary.

## Layer-2 measurement

The distinction between measurement on the success path and measurement on the fail-closed path comes from the architecture, not from the tool (L-27). Success path: a file that Stage A accepts in full. Fail-closed path: a file that Stage A refuses; there, `unresolved` is the correct result.

### State of the fork's PRs (all opened as evidence, none for merge)

| PR | Branch | File | Path | Cache | Auditor | Total | Result |
|---|---|---|---|---|---|---|---|
| #1 | `l2-first-run` | `Logic/Hydra.lean` | success | `cold`, `first_run` | `382b5a5` | 136.1 s | 20/20 `verified`, exit 0 |
| #2 | `l2-trivial` | `Logic/Hydra.lean` | success | `cold`, `first_run` | `382b5a5` | 137.0 s | 20/20 `verified`, exit 0 |
| #3 | `l2-medio` | `Algebra/Homology/Embedding/Connect.lean` | success (file) | `cold`, `first_run` | `382b5a5` | 137.6 s | probe `verified`; 29 `verified` / 10 `unresolved` |
| #4 | `l2-fanout` | `Data/Set/Defs.lean` | fail-closed | `cold`, `first_run` | `382b5a5` | 148.1 s | 37/37 `unresolved` (declared syntax) |
| #5 | `l2-trivial-w` | `Logic/Hydra.lean` | success | `warm` | `7f7238d` | 126.1 s | 20/20 `verified`, exit 0 |
| #6 | `l2-medio-w` | `Algebra/Homology/Embedding/Connect.lean` | success (file) | `warm` | `7f7238d` | 129.7 s | probe `verified`; 29 `verified` / 10 `unresolved`; exit 1 |
| #7 | `l2-fanout-failclosed-w` | `Data/Set/Defs.lean` | fail-closed | `warm` | `7f7238d` | 142.1 s | 37/37 `unresolved` because of `stage_a_unrecognized`; probe `unresolved` (correct, L-17) |
| #8 | `l2-fanout-success-w` | `Data/String/Defs.lean` (position 4, 8147 dependents) | success | `warm` | `7f7238d` | 137.6 s | probe `verified`; 9/9 `verified`; exit 0 |
| #9 | `l2-timeout-w` | `Logic/Hydra.lean`, `timeout-file-seconds: 5` | step 8 (infra) | `warm` | `7f7238d` | 119.3 s | `timeout`, exit 2, `infra_failed`, green job, `auditor-failed-infra` |

In #5–#8: `clock_origin: trigger`, `build_cache: hit`, `inspector: hit`, `project_dirty: false`, no environment signal and no timeout.

**PR #6:** Stage A accepts the whole file (no unrecognized item). The 10 `unresolved` declarations are specific declarations, identical to those of PR #3: 8 because of `set_option backward.*` outside the policy and 2 only because of `implemented_by_candidate` (`CategoryTheory.Limits.WalkingParallelPair.ctorIdx`, an attribute generated during elaboration; see `roadmap.md`).

**Budget:** 300 s; largest `warm` measurement, 142.1 s. Preparation dominates: in PR #5, checkout 33 s, `lake exe cache get` 63 s (even with a hit, it unpacks the `.ltar` files), audit 13 s. A note for Phase 1, not a priority.

### Cache workflows

- **D-61:** `auditor-warm-cache` saves the inspector and Mathlib caches on the base branch (run 39758479162).
- **A2:** the inspector is saved even when the job is red. Tested without depending on a hit (reference procedure in `maintenance.md`).
- **D-62:** the auditor leaves the workspace after installation; `project_dirty: false` in every report.

## Validation

| Item | Result |
|---|---|
| Suite (`ci.yml`, Linux) | 662 passed, 0 failed (runs 39758445713 on `7f7238d` and 39813452380 on `0c64a3e`) |
| Mutation | 6 groups, 135/135 detected, 0 survivors, 0 skipped (`maintenance.md`); 138/138 after the step-9 fix |
| `auditor-prep` (run 39812801650) | green; allow-list with 259 commands, 0 unclassified, 8651 modules; `gen_tcb_roots --check` exit 0; smoke test 20/20, `project_dirty: false` |
| Mathlib allow-list | regenerated in CI, byte-for-byte identical to the committed one (run 39696176700) |

## Limitations

L-1 to L-29 in `docs/limitations.md`. Those that weigh most on the reading of these results: L-1 and L-14 (kernel, compiler and inspector in the TCB), L-5 (`@[implemented_by]` is a candidate), L-9 (correspondence not audited), L-17 (what Stage A does not recognize brings down the file), L-25 and L-26 (Mathlib classification fail-closed on ambiguous cases, and self-reviewed), L-27 (success and fail-closed paths kept separate), L-28 (0 real uses of native evaluation in `Mathlib@e1b2403b`).

## Phase 1 agenda

P0 priorities in `docs/roadmap.md`: `@[implemented_by]` generated during elaboration, and the Stage A fail-closed rate (68 % of the 60 files with the highest fanout). Phase 1's research question (whether the semantic hypothesis is worth pursuing) remains open.

## Evidence for the unconditional closure (instruction 24)

The four criteria accepted by the reviewer, with the runs:

| Criterion | Evidence | Run |
|---|---|---|
| Step 9 re-run and qualified | PR #8 closed and reopened to produce a new audit with auditor `69ed9cf`, without touching the PR's code: `warm`, 135.6 s, 9/9 `verified`, `classification_review_status: author-self-review` in `outcome.json`. `@auditor report`: a single comment with `classificação: author-self-review (L-26)`; qualified Job Summary | audit [39826300196](https://github.com/Enzo47961/mathlib4/actions/runs/39826300196); comment [39827471933](https://github.com/Enzo47961/mathlib4/actions/runs/39827471933) |
| Suite | 674 passed, 0 failed, on `69ed9cf` (there were 666; the 8 new ones cover the L-26 line) | [39825726718](https://github.com/Enzo47961/auditor/actions/runs/39825726718) |
| Mutation | `ci` group 38/38 on `69ed9cf`, including the mutant that removes the summary line and the one that replaces "indeterminada" (undetermined) with a fixed `author-self-review` (equivalent, in the summary, to the real survivor of instruction 19). Consolidated state: 6 groups, **141/141**, 0 survivors, 0 skipped (`maintenance.md`) | [39826324751](https://github.com/Enzo47961/mathlib4/actions/runs/39826324751) |
| `auditor-prep` | green: 259 commands, 0 unclassified, `gen_tcb_roots --check` exit 0, smoke test 20/20 with the L-26 line in the summary | [39826330043](https://github.com/Enzo47961/mathlib4/actions/runs/39826330043) |

Published state: auditor `master` = `ad8f3d3` at closure (code run in the fork: `69ed9cfd1bf6016358d799d31113d5555cc71763`); fork `auditor-base` = `018d7db`.
