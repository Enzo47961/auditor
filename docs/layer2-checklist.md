# Layer 2 — execution checklist

**Who executes it:** the maintainer, under their own account. Nothing here is executed by the AI assistant: these are
public actions (repository, fork, PRs, comments), and the decisions along the way (abort, adjust,
continue) are human. The assistant analyses whatever is brought back.

**What it is for:** producing the layer-2 evidence of Phase 0 (`README.md`, "Status"; plan in
`docs/ci.md`). Phase 0 only closes with it; Phase 1 does not start before it.

"Instruction N" refers to the numbered decisions of the project's external reviewer.

Conventions: `$ME` = your GitHub account; `$AUD` = the auditor commit pinned in step 1; commands in
bash (Git Bash works). Each step has **Check** (what must be true before moving on) and,
where applicable, **Abort if**. When aborting: do not try to fix things midway; bring what you have (logs,
`outcome.json`, a screenshot of the job) and the step number.

## A failure that is not infrastructure (applies to every step)

Infrastructure is the runner, cache, network, timeout, `auditor-failed-infra`: the step is repeated or
aborted according to its **Abort if**. **A failure that is not infrastructure** is the auditor giving
a result it should not give, with the environment working:

| Signal | Examples |
|---|---|
| Unexpected false positive | the probe lemma `auditor_probe_*` does not come out `verified`; a Mathlib declaration that the PR did not touch comes out `Rejeitada`, `Não conforme` or `Não resolvido`; `native_auxiliary_axiom` in a file of the `Mathlib` library (the measurement at `e1b2403b` expects 0) |
| Allow-list diverging from the pinned Mathlib | `unknown_command`, `unclassified_command`, `syntax_extension_declared` or `metaprogramming_command` in a file the PR did not change; `auditor-gen-allowlist --check` ≠ 0; `gen_tcb_roots.py --check` ≠ 0 |
| TCB boundary | `tcb_boundary_undeclared`, `tcb_boundary_unresolved`, `extern_candidate`/`implemented_by_candidate` pointing to a constant from `Init`, `Lean`, `Std` or `Lake` |
| Inspector | `inspector_disagreement`, `missing_constants`, `inspector_field_missing` |

**What to do:**
1. Stop at the step where it appeared. Do not open the next PR.
2. Do **not** adjust the policy, the allow-list, `target_trusted_roots` or the auditor to make it
   pass. Do not repeat the run hoping for another result either: the auditor is deterministic, and a
   second identical run is not new evidence.
3. Bring: `report-*.json`, `outcome.json`, `summary.md`, the audited `.lean` file, the fork's
   commit and the step number.
4. The classification (a false positive of the auditor or a real finding in Mathlib) is a policy decision,
   taken outside the run. The measurement only continues after it.

---

## 0. Preconditions (before any public action)

- [ ] Layer 1 closed (2026-10-21: 115/115 mutations detected, suite 558 passed): mutation of the 5 groups has 0 survivors (`docs/proposed-improvements.md`,
      "Instruction 13 round"), and Q9 is decided (option a: `native_decide` never comes out
      `verified` in Phase 0). The measurement uses the final policy.
- [ ] Decided the visibility of the auditor's repository. **Technical constraint:** the fork's workflow
      calls the auditor's reusable workflow (`uses: $ME/auditor/...@$AUD`). A public Mathlib fork
      can only call a reusable workflow from a **public** repository (or from the same
      owner with access configured for private repositories, which requires the fork to be
      private too — and a fork of a public repository cannot be private). In practice: a public auditor,
      or copy the reusable workflow into the fork (see 3b).
- [ ] Is Mathlib `master` still on `leanprover/lean4:v4.36.0-rc1`? Check:
      `curl -sSfL https://raw.githubusercontent.com/leanprover-community/mathlib4/master/lean-toolchain`.
      It does not matter if it changed: the base is pinned to commit `e1b2403bdd31a2756e30282d62b3fa54cc95c869`
      (the same toolchain as the auditor). Note the date and the `master` commit on that day, for the report.

## 1. Pin the auditor

```bash
cd <auditor repository>
git status                      # Check: clean
git log -1 --format=%H          # this is $AUD
```

If publishing on GitHub (decision of step 0):

```bash
gh repo create $ME/auditor --public --source . --remote origin --push   # or --private (see 0)
```

**Check:** `gh api repos/$ME/auditor/commits/$AUD --jq .sha` prints `$AUD`.

## 2. Mathlib fork with a pinned base

```bash
gh repo fork leanprover-community/mathlib4 --clone=false        # creates $ME/mathlib4
git clone --filter=blob:none https://github.com/$ME/mathlib4 && cd mathlib4
git fetch https://github.com/leanprover-community/mathlib4 e1b2403bdd31a2756e30282d62b3fa54cc95c869
git switch -c auditor-base FETCH_HEAD
cat lean-toolchain              # Check: leanprover/lean4:v4.36.0-rc1
```

**Turn off Mathlib's own workflows in the fork** (they would run on every PR, on GitHub
runners, and pollute the measurement): on the `auditor-base` branch, remove Mathlib's `.github/workflows/*`
before step 4 (`git rm -r .github/workflows`), or disable them in Settings → Actions.

**Enable Actions in the fork:** Settings → Actions → General → "Allow all actions" (forks come with
Actions turned off). Workflow permissions: "Read repository contents".

## 3. Mathlib allow-list (human classification)

```bash
# in the fork's clone, branch auditor-base
lake exe cache get                                  # Check: finishes without error
pip install <path or URL of the auditor>@$AUD
auditor-gen-allowlist --project .                   # writes .auditor/allowlist.json
python -c "import json;print(json.load(open('.auditor/allowlist.json'))['unclassified'])"
```

- [ ] For each command in `unclassified`, classify it in `.auditor/classification.toml` with the
      criterion of `tools/gen_allowlist/classification.toml` (L-17): `metaprogramming` if it can
      execute compiled code during elaboration before Stage B, or if it hides another command from the
      column-0 check; `syntax_extension` if it introduces syntax; otherwise, `allowed`. When in doubt,
      fail-closed. Example of the format in `docs/maintenance.md`, "Project allow-list".
- [ ] Regenerate and check: `auditor-gen-allowlist --project . --check` exits with 0 and `unclassified`
      is empty.
- [ ] The classification is policy: another person reviews it before the commit.

```bash
git add .auditor && git commit -m "auditor: Mathlib allow-list (e1b2403b, v4.36.0-rc1)"
```

**TCB roots (D-42).** The auditor's `target_trusted_roots` was generated from this same
commit. Check that the fork has not diverged from it (with the dependencies downloaded by the `cache get` above):

```bash
python <auditor>/tools/gen_tcb_roots.py --sysroot "$(lean --print-prefix)" --project . --root Mathlib --check
```

**Check:** it exits with 0. The generator checks each package in `.lake/packages` against the `rev` in
`lake-manifest.json`, and the import closure against `src/auditor/data/target_trusted_roots/<toolchain>.json`.
In the fork, `HEAD` (`auditor-base`) is not `e1b2403b`: the output must say `fork de medição: HEAD … =
e1b2403b… + só .github/ (D-54)` (measurement fork: HEAD … = e1b2403b… + only .github/). Any other difference from `e1b2403b` fails (L-24). In a
shallow checkout, `e1b2403b` must be present (`fetch-depth: 2`).

**Allow-list (D-52):** `auditor-gen-allowlist` uses only Mathlib's `@[default_target]` library
(`Mathlib`); the `libraries` field of the generated file must be `["Mathlib"]`. The
`Cache` library, which `lake exe cache get` builds, is left out.

**Abort if:** `lake exe cache get` fails; the generator fails to import Mathlib (bring the
output); the `unclassified` list has commands whose effect cannot be determined by reading their definition;
`gen_tcb_roots.py --check` exits with anything other than 0 (bring the output: the TCB boundary changed).

**Security note:** the generator runs Mathlib's initializers (D-39). Run it only on the
commit pinned above, never on a PR branch.

## 3b. Local smoke test (before any PR)

Runs `auditor-ci` on **a single Mathlib file at the pinned commit**, outside the PR flow, in the
fork's clone (branch `auditor-base`, with the `cache get` and the allow-list from step 3).

```bash
mkdir -p smoke
auditor-ci run Mathlib/Logic/Hydra.lean --policy <auditor>/policy.toml --out-dir smoke \
  --build-cache miss --timeout-total-first-run 1800 \
  --started-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "exit=$?"
python -c "import json;o=json.load(open('smoke/outcome.json'));print({k:o[k] for k in ('cache_state','first_run','infra_failed','exit_code')})"
grep -rlE "allowlist_unavailable|toolchain_mismatch|inspector_build_failed|sysroot_mismatch|search_path_unrecognized|tcb_boundary_undeclared|unknown_command" smoke/ || echo "no environment signal"
```

**Check:**
- `outcome.json`: `cache_state: cold`, `first_run: true`, `infra_failed: false`, `exit_code` 0;
- the `grep` prints "no environment signal" (in particular, no `allowlist_unavailable`);
- in `report-*.json`, every declaration of `Hydra.lean` comes out `verified`. If any does not, see
  "A failure that is not infrastructure" above.

**Why locally and with `--build-cache miss`:** outside the runner there is no Actions cache, so the
cache state is the declared one. `--build-cache miss` exercises the first-run path (`cold`,
`first_run: true`, extended budget). The local extended budget is 1800 s, not 900 s,
because a personal machine is not the runner, and this step does not measure time. The test checks the
environment (toolchain, allow-list, `target_trusted_roots`, inspector) and the outcome logic. The
first real run on the runner is step 5.

**Abort if:** any **Check** item fails. Do not open any PR (not even step 5's).
`smoke/` is not committed.

## 4. Workflows in the fork

```bash
mkdir -p .github/workflows
cp <auditor>/ci/templates/auditor-{tier1,label,report,warm-cache}.yml .github/workflows/
sed -i "s#OWNER/auditor#$ME/auditor#g; s#AUDITOR_SHA#$AUD#g" .github/workflows/auditor-*.yml
grep -n "OWNER\|AUDITOR_SHA" .github/workflows/auditor-*.yml     # Check: nothing
git add .github/workflows && git commit -m "auditor: workflows (layer 2)"
git push -u origin auditor-base
gh repo edit $ME/mathlib4 --default-branch auditor-base
```

**Why change the default branch:** `workflow_run` (label) and `issue_comment` (`@auditor report`)
only run from the default branch's workflows.

**3b (if the auditor is not public):** also copy the auditor's `.github/workflows/auditor-tier1.yml`
into the fork under another name (e.g. `auditor-tier1-impl.yml`) and change the template's `uses:`
to `./.github/workflows/auditor-tier1-impl.yml`. The auditor checkout inside the job still
needs read access to the private repository (a token): in that case, stop and bring the
situation back, because it changes the security model (D-24).

**Check:** `gh workflow list -R $ME/mathlib4` shows `auditor-tier1`, `auditor-label`,
`auditor-report` (and no active Mathlib workflow).

## 4b. Warm the cache on the base branch (D-61)

Step 4's push to `auditor-base` already triggers `auditor-warm-cache`. To run it by hand:

```bash
gh workflow run auditor-warm-cache.yml -R $ME/mathlib4 --ref auditor-base
gh api repos/$ME/mathlib4/actions/caches --jq '.actions_caches[] | "\(.ref)\t\(.key)"'
```

**Check:** two entries with `ref` = `refs/heads/auditor-base`: `auditor-inspector-Linux-$AUD-…` and
`mathlib-cache-Linux-…-<auditor-base commit>`. Repeat whenever `auditor-base` or `$AUD`
change.

**Why:** the GitHub Actions cache is isolated per ref. A PR only restores what it saved itself
or what the base branch saved. Without this step, every new PR starts `cold`.

## 5. First run (cold cache) — not a steady-state measurement

```bash
git switch -c l2-first-run auditor-base
# minimal change to a leaf file: one comment line
printf '\n-- auditor: primeiro run\n' >> Mathlib/Logic/Hydra.lean
git commit -am "l2: first run" && git push -u origin l2-first-run
gh pr create -R $ME/mathlib4 --base auditor-base --head l2-first-run --title "l2: first run" --body "layer-2 measurement"
```

**Check** (in the Job Summary and in the `outcome.json` of the `auditor-report` artifact):
- `cache_state: cold`, `first_run: true`;
- the job finished (green if nothing was rejected; red only for a real rejection);
- if it went past 300 s: `cache_cold_extension: true` and the `auditor-first-run` label on the PR;
- the "Mathlib cache (save)" step ran without error.

**Abort if:** any file comes out with `allowlist_unavailable`, `toolchain_mismatch`,
`inspector_build_failed`, `sysroot_mismatch` or `search_path_unrecognized` (an environment failure,
not a measurement one); the job exceeds the `timeout-minutes` of 45; the label applied is
`auditor-failed-infra` without an explanation in the summary.

## 6. Mechanical choice of the files

```bash
python <auditor>/tools/layer2/fanout.py . --root Mathlib --top 40 --json fanout.json --expect-commit e1b2403bdd31a2756e30282d62b3fa54cc95c869 > fanout.md
python <auditor>/tools/layer2/native_usage.py . --root Mathlib --json native_usage.json > native_usage.md
```

**Check:** both exit with 0. `fanout.json` carries `provenance.commit` equal to the base commit. If
the checkout is at another commit, `fanout.py` exits with 2 and prints no ranking: go back to the
`auditor-base` branch. `native_usage.md` answers the question of instruction 13: what share of
Mathlib's declarations uses native evaluation, and in which areas. Expected value at commit `e1b2403b`:
no declaration of the `Mathlib` library (Mathlib's linter forbids it; usage is confined to
`MathlibTest`, which is not part of the library).

Result observed at commit `e1b2403b` (8651 modules): the first 19 positions are
infrastructure (`Mathlib.Init`, `Mathlib.Tactic.*`, `Mathlib.Lean.*`, `Mathlib.Util.*`), which
Stage A generally classifies as metaprogramming (fail-closed) or which have no declarations. The
old "core" `Mathlib/Logic/Basic.lean` **no longer exists** at this commit; the equivalent is
`Mathlib/Basic/Logic/Basic.lean` (position 24, 8072 dependents). The first mathematical module of the
ranking is `Mathlib/Data/Set/Defs.lean` (position 20, 8092 dependents).

Suggested choice (the reviewer decides and records it):

| PR | File | Criterion |
|---|---|---|
| trivial | `Mathlib/Logic/Hydra.lean` (0 dependents) or another module with `transitive = 0` | a leaf; a comment/docstring-only change |
| medium | a file with `imports_transitive` close to the median of `fanout.json` (783 at commit `e1b2403b`) | a new lemma, with a short proof |
| fanout, success path (L-27) | the highest-fanout file whose Stage A has no unrecognized item; at commit `e1b2403b`, `Mathlib/Data/String/Defs.lean` (position 4, 8147 dependents; the reviewer's choice, instruction 21). `Mathlib/Lean/Name.lean` (position 3) only as an additional measure | a trivial new lemma at the end of the file |
| fanout, fail-closed path (L-27) | `Mathlib/Data/Set/Defs.lean` (the ranking's first mathematical module; declares syntax) | a trivial new lemma at the end of the file; the probe `unresolved` is the expected result |
| (optional) worst audit cost | `Mathlib/NumberTheory/LSeries/PrimesInAP.lean` (largest forward closure: 3403 modules) | measures the cost of `lake build` + inspector, which grows with the forward closure (D-38) |

## 7. The 3 measurement PRs (steady state, after step 5)

After step 4b (base cache warmed). For each PR (`trivial`, `medio`, `fanout`, `fanout-failclosed`):

```bash
git switch -c l2-<name> auditor-base
# edit the chosen file; for "medio"/"fanout", at the end of the file:
#   theorem auditor_probe_<name> : (2 : Nat) + 2 = 4 := rfl   (Nat, not ℕ: base files do not have the notation)
git commit -am "l2: <name>" && git push -u origin l2-<name>
gh pr create -R $ME/mathlib4 --base auditor-base --head l2-<name> --title "l2: <name>" --body "layer-2 measurement"
```

**Check** on each one:
- `cache_state` is `warm` or `delta` (never `cold` — if it is, the cache was evicted or the key changed:
  abort that PR, note it, run it again);
- `clock_origin: trigger`;
- `auditor_probe_<name>` appears in the report as `verified` (in `fanout-failclosed`, `unresolved` with
  `syntax_extension_declared`, which is the expected result);
- `tcb.dependencies.project_dirty: false` (D-62);
- timings: `setup_elapsed_s`, `audit_elapsed_s`, `elapsed_s`, the file's duration.

**Abort if:** the edited file comes out `unknown_command` (incomplete allow-list: go back to step 3);
`inspector_disagreement` or `missing_constants` appears (bring the report: it is a finding, not noise);
`auditor_probe_<name>` does not come out `verified`, or any other signal of "A failure that is not
infrastructure" (table at the start).

## 8. Timeout path (`auditor-failed-infra`)

On a new PR's branch, edit the fork's `.github/workflows/auditor-tier1.yml` and add to
`with:` the line `timeout-file-seconds: 5`. Open the PR touching a `.lean` file.

**Check:** the file comes out `timeout` (`timeout_kind: file`), `exit_code: 2`, the job stays **green**,
and the PR gets `auditor-failed-infra`. Then close the PR without merging.

## 9. Comment on human request

On one of the PRs of step 7, a collaborator comments `@auditor report`.
**Check:** a comment with the summary appears, starting with "Pedido por um humano" (requested by a human). A
comment from someone without access to the repository does **not** trigger anything.

## 10. Collect and deliver

```bash
mkdir -p l2 && for pr in <numbers>; do
  run=$(gh run list -R $ME/mathlib4 --workflow auditor-tier1.yml --branch l2-<name> --limit 1 --json databaseId --jq '.[0].databaseId')
  gh run download $run -R $ME/mathlib4 -n auditor-report -D l2/pr-$pr
done
python <auditor>/tools/layer2/timings.py l2 > l2/timings.md
```

**Expected format of the measurement report** (one file, e.g. `l2/RELATORIO.md`):

1. Context: the auditor's commit (`$AUD`), the fork's base commit (`e1b2403b`), the date, the Mathlib `master`
   commit on that day, the runner (`ubuntu-24.04`, pinned by D-55; image version in the job log).
2. A table, one row per PR (first run, trivial, medium, fanout, timeout):

   | PR | file | change | `cache_state` | `first_run` | preparation (s) | audit (s) | total (s) | file duration (s) | `exit_code` | verified/rejected/unresolved count | labels | job conclusion |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|

3. `l2/timings.md` (output of `timings.py`) and `fanout.md` (top 40), with the choice of files and the
   `provenance` of `fanout.json`.
4. **Native evaluation** (instruction 13), in two measures:
   - over the whole of Mathlib: `native_usage.md`, with the share of declarations that use `native_decide`,
     `+native`, `native := …` or `bv_decide`, total and per area (`Mathlib/<Area>`);
   - in each PR: how many declarations of the report have `native_auxiliary_axiom` among their reasons.
     Expected: 0 in the measurement PRs. Anything other than 0 is a finding.
5. The complete artifacts: `l2/pr-*/outcome.json`, `summary.md`, `report-*.json`.
6. Notes: any abort/repeat, with the reason; the size of `~/.cache/mathlib` (log of the
   "Mathlib cache (save)" step); whether the event's `updated_at` matched the push (D-30).
