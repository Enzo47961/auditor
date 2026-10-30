# User study (sub-phase 1c): data

Methodology: `docs/user-study.md`. Invitation: `docs/user-study-invite.md`.

| File | Content | Produced by |
|---|---|---|
| `selection.json` | the 31 PRs merged after `e1b2403b`, the criteria applied, the 13 eligible ones and their strata | `tools/phase1/study_select.py` |
| `patches/` | the PRs' diffs, applicable on top of `e1b2403b` | `tools/phase1/study_select.py` |
| `audit.json` | the audit of each eligible PR and the per-PR (B) exclusion (run 39936018705); superseded by the per-declaration exclusion (instruction 28) | `tools/phase1/study_audit.py` |
| `prs.json` | the 10 PRs of the study (mechanical rule: 5 per stratum, in merge order) | `tools/phase1/study_run.py prs` |
| `seed.txt` | seed of the draw, `1818766798`, **published on 2026-10-23**, before any reply to the invitation | `secrets.randbelow(2**31)` |
| `alerts.json` | alerts of the 10 PRs as the participants see them (with the defects), **frozen before any form**: reports from **run 39977160187** (auditor `ae9f791`) | `study_audit.py --prs`, `study_run.py alerts` |
| `categories.json` | five-category taxonomy (instruction 30) over `alerts.json` | `study_run.py classify` |
| `defects.json`, `defects/` | the planted defects (instructions 27 and 28): the defect-only diff, ground truth, expected result | checked by `tools/phase1/study_audit.py --defects` (`auditor-study`, `defects` mode) |

`alerts.json`, `categories.json`, `defects.json`, `prs.json` and `seed.txt` are frozen artifacts of the pre-registration (`docs/user-study.md`, section 11). They are kept byte-for-byte as committed, including any Portuguese text inside them, so that their SHA-256 hashes stay valid.

## Planted defects: how to check them

```
python tools/phase1/study_audit.py <mathlib at e1b2403b> --selection study/selection.json \
    --patches study/patches --policy policy.toml --out out/ --defects study/defects.json
```

For each defect, the tool applies the PR's patch and the defect's patch, audits the files and checks three things:
- the expected declaration comes out with the expected status;
- the reason is the expected one;
- the reason is **not** a known cause (`ctorIdx`, `backward.*`, `target_defines_executable_code`).

If compilation fails, it saves the Lean log (the auditor's report does not include the message). Approved checks: runs 39973055204 and 39977153820.

## Lesson (defect B, instruction 29)

**Planted-defect fixtures reuse the form of benchmark case C08 (a dedicated implementation); inventing one from scratch introduces a compilation error that masks the defect.**

The first version of defect B used `@[implemented_by Nat.add]`. Lean rejects that target ("Invalid `implemented_by` argument"). Without the substitution, `native_decide` evaluated the true value (`2 * 3 = 6`) and refused the proposition. The auditor saw only `compile_failure`, not the defect (run 39971602437). The fix uses a dedicated implementation (`private def iInterIndexImpl (a b : ℕ) : ℕ := a + b`), in the form of C08 (`benchmark/lean/Cheat/C08.lean`).
