# User study (Phase 1, sub-phase 1c)

```
status: methodology approved (instruction 27); invitation approved; PR selection and planted defects ready; metrics pre-registered (section 11); recruitment pending
classification: author-self-review (L-26)
```

**Question (instruction 24).** Does the tool reduce net human review time? That is, T_net = T_conventional − T_assisted > 0, with a false-alarm rate below 30 %.

*Terminology.* "Instruction N" refers to the numbered decisions of the project's external reviewer. Status values such as `Rejeitada` (rejected), `Não resolvida` (unresolved) and `Não conforme` (non-conforming) are quoted exactly as the auditor prints them in its reports.

## 0. Scope: option (B) of instruction 26, per declaration (instruction 28)

**Granularity (instruction 28, Q1 (a)).** The exclusion is **per declaration**, not per PR. Per PR, it removed 9 of 13 PRs (section 8): `backward.*` appears in almost every file, often in one declaration out of 80. The PR stays in the study, and alerts from known causes are handled as follows:
- **Known causes** (instructions 26 and 28):
  - `implemented_by_candidate` from a generated `ctorIdx` (L-34);
  - `set_option_unrecognized`/`set_option_unattributed` from a `backward.*` option;
  - `target_defines_executable_code` from a delaborator or a `positivity` extension in a mathematical file (L-35).
- **Briefing:** it warns about the known causes but **does not say "ignore"**. It says: "these alert types have a known cause and are being fixed; if you encounter them, record the time you spend on them separately". Participants are asked to report the time, not to ignore the alerts.
- **False-alarm rate of the criterion (< 30 %):** measured **only over alerts that are not from a known cause**.
- **T_net:**
  - the time spent on known-cause alerts is measured separately and **excluded from the main T_net**;
  - the report gives both numbers: **T_net without known causes** (the main one) and **T_net with them** (for transparency).
- **Alert classification:** each alert is assigned to a cause mechanically, from the auditor's own report (reason code and detail), before the forms are read.

The original text of option (B), below, still holds for the goal and for the record of the scope.

### Option (B), text of 2026-10-23

**The sample excludes the cases of generated `ctorIdx` and of `backward.*` options.**
- **Why:** with the current tool, 28.6 % of hard correct proofs come out `Não resolvida` because of these two known causes (L-31, L-34). Both are fail-closed, and both are P0 items of Phase 2. Measuring the full configuration now would give a negative T_net for the wrong reason: not because the tool does not help, but because of two causes of false positives that are already known to change.
- **What the result therefore measures:** the value of the tool within the scope it covers, not in the production configuration.
- **When this is corrected:** Phase 2, after fixing the two causes, re-measures with the full sample.
- **This statement is part of the result** and accompanies any citation of it.

## 1. Participants

- **3 real Mathlib reviewers**, or at least 2, with the limitation recorded. Each participant's experience as a Mathlib reviewer is stated in the result, without identification unless they consent.
- **Recruitment:** the maintainer sends the invitation (`docs/user-study-invite.md`) after the project reviewer has reviewed the text.
- **Participation is voluntary;** anyone may withdraw at any time.
- **Estimated time:** 2 to 3 hours per participant (section 4).

## 2. PRs: 10 real ones, in the measurement fork

- **Source:** real Mathlib PRs merged after `e1b2403b`, re-applied in the fork (`Enzo47961/mathlib4`, branch `auditor-base`) as measurement PRs. `auditor-tier1` audits each one.
- **Mechanical selection**, with the criteria published before the choice:
  - applies cleanly on top of `e1b2403b`;
  - changes 1 to 5 `.lean` files, with at most 300 diff lines;
  - does not touch `Tactic/`, `Lean/` or `Util/` (mathematical content);
  - the order of choice is the merge order in Mathlib.
- **Strata (instruction 24):**
  - 5 from the **success path** (Stage A accepts every changed file);
  - 5 from the **fail-closed path** (some changed file has an item that Stage A does not recognize).
- **Option (B) exclusion, decided by the auditor's own report:** a PR leaves the draw if some audited declaration is `Não resolvida` because of `implemented_by_candidate` from a generated `ctorIdx`, or because of `set_option_unrecognized`/`set_option_unattributed` from a `backward.*` option. The list of excluded PRs, with the reason for each, is published with the result. (Superseded by the per-declaration exclusion of section 0.)
- **Planted defect (approved in instruction 27).** It measures whether the tool helps a reviewer find a defect they would otherwise miss, and not only whether it saves time on correct PRs.
  - **Condition 1: injected into a real PR, never constructed.** The defect is introduced, as a minimal change, into one of the selected real PRs (re-applied on top of `e1b2403b`). The rest of the PR is untouched, and the participant cannot tell the PR apart by inspection.
    - **PR A (success stratum):** a `sorry` in a dependency 3 imports away from the PR's main file. The change to the dependency is part of the diff, as in any PR that touches more than one file.
    - **PR B (fail-closed stratum):** a lying `@[implemented_by]` with `native_decide` in a declaration of the PR.
    - **Formal ground truth:** a proof of the negation of what the defect "proves", or the `sorry` itself (`sorryAx` in the closure), checked as in the benchmark (`docs/benchmark.md`).
  - **Condition 2: three outcomes, reported separately, never aggregated.** For each planted defect:
    - **(a)** the tool flagged it (`Não resolvida`/`Rejeitada`), and the participant investigated and found the defect. This measures the tool's value;
    - **(b)** the tool flagged it, and the participant ignored the alert and approved. This measures alert noise;
    - **(c)** the tool did not flag it. This should not happen, because the defect is fail-closed by construction; if it does, it is a **critical finding** and goes into L-32.
  - **Notice to participants:** the invitation says that some PRs may contain planted defects, without saying which.
  - **If all 3 participants veto planting:** the paragraph is removed from the invitation, all 10 PRs stay real, and this limitation is recorded: "the study did not measure the reviewer's ability to find planted defects, because the participants chose not to take part in that component". The study continues; Phase 2 may re-measure with planting if willing reviewers are found.

## 3. Design: crossover, with randomized order

- Each PR is reviewed by **2 different participants**: one **with** the auditor (the PR's summary and report) and one **without** it (the diff only).
- Nobody reviews the same PR twice. There are 20 reviews in total, about 7 per participant, half with the auditor and half without.
- **Conflict of interest (instruction 27):** a participant is never assigned their own PR. If one of the 10 PRs was authored by a participant, that participant is not assigned that PR, and their effective sample is 9, not 10. The draw applies this constraint before distributing, and the authorship of each PR is published with the assignment.
- **The assignment and the order are randomized** with a seed published before the start, to control for learning effects and PR difficulty.
- **"Without auditor" condition:** the participant receives the PR's diff (a commit link, without the PR page in the fork, which shows the summary).
- **"With auditor" condition:** the participant receives the PR page in the fork, with the Job Summary and the report.
- **What each review asks for:** decide whether the PR can be merged from the point of view of proof integrity (`sorry`, axioms, native evaluation, code that runs during elaboration, risky commands). Statement correspondence and style are out of scope, as in the auditor.

## 4. Measures

Each participant records in a form, per review:
- start and end of the review;
- verdict (sound / not sound / don't know) and the problems found;
- **in the with-auditor condition:** the time spent reading the report, and whether any alert seemed false (with the reason).

**Derived measures, always per PR and per stratum, never only aggregated:**

| Measure | Definition |
|---|---|
| T_conventional, T_assisted | review time without and with the auditor, for the same PR |
| **T_net** | T_conventional − T_assisted, per PR; result = **median** over the 10 PRs |
| False-alarm rate | alerts **that are not from a known cause** (section 0) that the participant and the ground truth (or the PR's acceptance in Mathlib) judge unfounded / alerts that are not from a known cause, per PR (superseded by section 11) |
| Known-cause alerts | count and time, per cause (`ctorIdx`, `backward.*`, delaborator/`positivity`), reported separately |
| Main T_net × T_net with known causes | the main one excludes the time spent on known-cause alerts; the second includes it, for transparency |
| Interpretation time | the part of T_assisted spent reading the report |
| Perceived false negative | an integrity problem found by the participant and not flagged by the auditor |
| Planted defect | outcomes (a), (b) and (c) of section 2, per defect and per condition (with/without auditor), kept separate |

The cost per participant is about 7 reviews of 15 to 25 minutes, plus a 15-minute briefing: **2 to 3 hours**.

## 5. Criteria (instruction 24)

- **Acceptance:** median T_net > 0, with a false-alarm rate < 30 %.
- **Otherwise:** record as **L-32**: "T_net is X s (target: > 0); false-alarm rate is Y% (target: < 30%)".
- **Kill criterion:** T_net < 0 and false alarms > 50 %. In that case the tool increases human work, and Phase 2 is blocked until a follow-up study shows T_net > 0.
- **Phase 1 does not fail because T_net ≤ 0;** it fails by not measuring, or by measuring with a biased sample. The option (B) exclusion is declared precisely so that it is not a hidden bias.

## 6. Limitations (declared before the numbers)

- **Size:** 3 participants and 10 PRs give a preliminary signal, not a statistical conclusion about Mathlib as a whole. There will be no significance test.
- **Scope:** the option (B) exclusion makes the result unrepresentative of the production configuration (section 0).
- **Time:** self-reported.
- **Recruitment:** participants are volunteers recruited by the maintainer (selection bias). The classification used by the tool is self-reviewed (L-26).
- **PRs re-applied on top of `e1b2403b`,** not the original PRs at the time of their real review.
- **Planted defects** are artificial by definition.

## 7. Data and publication

- **Raw data:** anonymized forms (participant A, B, C), times, verdicts and alerts, published with the result.
- **Names:** only with each participant's explicit consent.
- **Mandatory qualification everywhere:** the classification is self-reviewed (L-26), and the scope is that of option (B).
- **Result:** recorded on this page and, if applicable, as L-32.

## 8. Result of the selection and of the (B) exclusion: stop for a decision (2026-10-23)

**Mechanical selection** (`tools/phase1/study_select.py`; `study/selection.json`): of the 31 PRs merged into Mathlib after `e1b2403b`, **13 are eligible**, 8 in the success stratum and 5 in the fail-closed one. The others were dropped for being CI, documentation or infrastructure, for having more than 5 files, or for a diff that does not apply.

**(B) exclusion, per PR** (`tools/phase1/study_audit.py`; `study/audit.json`; run 39936018705): **9 of the 13 excluded**.

| PR | Stratum | Exclusion | `verified` / declarations |
|---|---|---|---|
| #45105 | fail-closed | `backward.*` | 0/248 |
| #45097 | fail-closed | kept | 229/432 |
| #45102 | success | `backward.*` | 82/83 |
| #43841 | success | kept | 0/88 (only `target_defines_executable_code`: one delaborator) |
| #44400 | success | kept | 62/62 |
| #44425 | fail-closed | `backward.*`, `ctorIdx` | 0/175 |
| #44511 | fail-closed | `backward.*` | 222/636 |
| #44969 | fail-closed | `backward.*` | 90/293 |
| #45117 | success | `backward.*` | 76/77 |
| #44973 | success | `backward.*` | 88/117 |
| #45025 | success | kept | 114/114 |
| #45180 | success | `backward.*` | 73/74 |
| #45114 | success | `backward.*` | 177/178 |

**Kept:** 3 from the success stratum (#43841, #44400, #45025) and 1 from the fail-closed one (#45097). Six short of the 10.

**Finding 1: `backward.*` is in almost every changed file.** In 5 of the 9 excluded PRs, the cause is **one** declaration out of 74 to 178. Excluding per PR drops the whole PR because of one declaration.

**Finding 2: the environment rule of L-33a fires on mathematical files.** The flagged constants (`target_defines_executable_code`) are:
- **delaborators:** hand-written (`@[delab …]`, such as `WithAbs.delabToAbs`) or generated by `notation`/`notation3` (`…_delab_app_…`);
- **`positivity` extensions** (`@[positivity]`): `evalIntervalLength`, `evalGelfandRadius`.

Both are code that the elaborator executes: delaborators when formatting messages during elaboration; `positivity` extensions when the tactic is used. Under L-33a, `Não resolvida` is the correct (fail-closed) result. But it is a **coverage cost that had not been measured**: in #43841, a single delaborator brings down all 88 declarations of the file. This cost appeared in 5 of the 13 PRs. In files with `notation`, it adds to Stage A's fail-closed.

**Decision requested from the project reviewer** before the invitation is sent and the defects are injected: report of 2026-10-23, questions 1 and 2.

**Decision (instruction 28):**
- **Q1:** option (a), per-declaration exclusion, as specified in section 0. The 13 eligible PRs stay in the study.
- **Q2:**
  - L-35, with its reach measured over the whole of Mathlib;
  - delaborators and `positivity` as a known cause in 1c;
  - Phase 2 distinguishes hand-written delaborators (correctly fail-closed) from toolchain-generated ones (TCB candidates).
- **Planted defects:** in declarations whose alert is **not** from a known cause, checked with the auditor:
  - PR A in a success-stratum PR (#44400 or #45025);
  - PR B in #45097, or also in a success-stratum PR if #45097 has no eligible declaration.

**Defects injected and checked** (`study/defects.json`, `study/defects/`; `auditor-study`, `defects` mode, run 39973055204, auditor `dce313c`):

| Defect | PR (stratum) | Change | Ground truth | Auditor result |
|---|---|---|---|---|
| A | #45025 (success) | `sorry` in the proof of `isUnit_mul_self_iff` (`Algebra/Group/Commute/Units.lean`), 3 imports away from the PR's file. The PR's new lemma, `Units.isSquare_coe_iff`, uses it. | `sorryAx` in the closure | both declarations come out `Rejeitada`, with `sorryAx_detected` |
| B | #45097 (fail-closed) | `@[implemented_by iInterIndexImpl]` (addition) on a `private` helper that computes `a * b`, plus `native_decide` proving `iInterIndexAux 2 3 = 5` inside `measure_iInter_eq_iInf_measure_iInter_le`. Without the defect, the file is 19/19 verified. | `2 * 3 = 6 ≠ 5`; only the compiled code says 5 | `Rejeitada`, with `implemented_by_reaches_native_eval` |

Neither reason is a known cause. (Defect A later moved to #44400; see section 9.)

**Briefing: where the defect is** (instruction 29). The briefing states explicitly that a planted defect **is not necessarily in the declaration the participant is looking at**: it may be in a dependency. This is the case of defect A, whose `sorry` is 3 imports away from the PR's file. When an alert points to an origin in another file (the `origins` of `sorryAx_detected`), the participant should follow it there. The invitation does not include this nuance; it belongs to the briefing.

**First attempt at B: our error.** We used `Nat.add` as the `implemented_by` target, and Lean rejects it. Without the substitution, `native_decide` evaluated the true value and refused the proposition (run 39971602437). This was fixed with a dedicated implementation, in the form of benchmark case C08.

## 9. Data collection (instruction 29, item 5)

Prepared before the participants' replies, so that 1c can start without delay. Tool: `tools/phase1/study_run.py`, tested in `tests/maintenance/test_phase1_tools.py`.

**1. The 10 PRs** (`study/prs.json`, `study_run.py prs`). The mechanical rule of section 2 picks 5 PRs per stratum, in Mathlib merge order, among the 13 eligible ones:
- **success:** #45102, #43841, #44400, #45117, #44973;
- **fail-closed:** #45105, #45097, #44425, #44511, #44969.

Under this rule, #45025 is the 6th of the success stratum and is left out. Therefore **defect A was moved to #44400**, the other option authorized by instruction 28. The new defect is a `sorry` in `Set.mul_mem_mul` (`Algebra/Group/Pointwise/Set/Basic.lean`), 3 imports away from `RingTheory/MvPowerSeries/Restricted.lean`. Through `to_additive`, the `sorry` reaches `Set.add_mem_add` and from there `tendsto_sup'_antidiagonal_cofinite`. `MvPowerSeries.tendsto_antidiagonal`, `IsRestricted.mul`, `IsRestricted.subring` and the instances the PR changes all depend on it. The #45025 version is recorded in `study/defects.json` (`history`).

**2. Published seed:** `1818766798` (`study/seed.txt`). It was generated and published on 2026-10-23, before any reply to the invitation. The draw depends only on the seed, on `study/prs.json` and on the list of participants, so anyone can reproduce it.

**3. Draw** (`study_run.py assign`). Each PR goes to 2 different participants, one **with** and one **without** the auditor. The constraints:
- nobody reviews a PR they authored (conflict of interest, instruction 27);
- the load is balanced (7, 7, 6 with 3 participants);
- for each participant, the difference between reviews with and without the auditor is at most 1;
- the order of each participant's reviews is random.

The draw uses rejection sampling: the first attempt of the generator that satisfies the constraints is used, and the attempt number is published. The participants' identities (`study/reviewers.json`, with GitHub usernames for the conflict-of-interest check) are **not** version-controlled. The published assignment uses only A, B and C, and lists the (PR, participant) pairs excluded for conflict of interest.

**4. Form** (`study_run.py forms`): one CSV per participant, with the reviews in the drawn order.

| Column | Content |
|---|---|
| `order`, `pr`, `condition` | filled in by the draw (`with` = with auditor, `without` = without) |
| `start`, `end` | start and end of the review (ISO 8601, e.g. `2026-11-03T14:05`) |
| `verdict` | `integro` (sound), `nao_integro` (not sound) or `nao_sei` (don't know) |
| `problems_found` | the integrity problems found, as free text |
| `report_reading_min` | with auditor only: minutes spent reading the report |
| `causes_judged_false` | with auditor only: the **causes** (file:code[:option], as in the report) whose alert seemed false, separated by `;`, with the reason in `notes` (instruction 30) |
| `known_cause_min` | with auditor only: minutes spent on known-cause alerts (section 0) |
| `noncoverage_min` | with auditor only: minutes spent on non-coverage alerts (`Não resolvida` due to fail-closed; instruction 30) |
| `notes` | free text |

**5. Alerts** (`study_audit.py --prs study/prs.json --defects study/defects.json`, then `study_run.py alerts`). The auditor runs on the 10 PRs **as the participants see them**, i.e. with the planted defects applied. Each alert (non-`verified` declaration) is assigned to a cause mechanically, **before** the forms are read. An alert is a known-cause alert when all its reasons are known causes.

**6. Final report** (`study_run.py report`, in `study/result.json`). It contains:
- per PR and per stratum (never only the aggregate): T_conventional, T_assisted, **main T_net** (without the time on known causes), T_net with known causes, reading time and alerts (known-cause and other);
- the **false-alarm rate** (as defined in section 11);
- the median per stratum and overall;
- the **planted defects**: per defect and per condition, whether the participant found the defect, and, in the with-auditor condition, outcome (a), (b) or (c) of section 2;
- the criteria of section 5, written into the result itself.

**Briefing (15 minutes), fixed content:**
- what the auditor checks and what it does not;
- the known causes, and the request to record the time spent on them (section 0, without saying "ignore");
- that the planted defect may be in a dependency, not in the main declaration (section 8);
- how to fill in the form.

## 10. Alerts of the 10 PRs and a question before the first review (2026-10-23)

The auditor ran on the 10 PRs as the participants see them, with the defects applied (`auditor-study`, `study` mode, run 39977160187, auditor `ae9f791`). The defects were checked in run 39977153820. All 10 PRs compile. The alerts are in `study/alerts.json`, assigned mechanically before any form.

| PR | Stratum | `verified` | Alerts (declarations): known / other | Distinct causes (file + reason): known / other |
|---|---|---|---|---|
| #45102 | success | 82/83 | 1 / 0 | 1 / 0 |
| #43841 | success | 0/88 | 88 / 0 | 1 / 0 |
| #44400 (defect A) | success | 386/441 | 0 / 55 | 0 / 2 (the `sorry`) |
| #45117 | success | 76/77 | 1 / 0 | 1 / 0 |
| #44973 | success | 88/117 | 29 / 0 | 2 / 0 |
| #45105 | fail-closed | 0/248 | 0 / 248 | 2 / 1 |
| #45097 (defect B) | fail-closed | 227/434 | 0 / 207 | 0 / 5 (2 from the defect) |
| #44425 | fail-closed | 0/175 | 132 / 43 | 3 / 1 |
| #44511 | fail-closed | 222/636 | 2 / 412 | 3 / 3 |
| #44969 | fail-closed | 90/293 | 186 / 17 | 12 / 1 |

Counting by distinct cause, there are 25 known-cause alerts and 13 others. Of the 13, 4 come from the planted defects. The remaining 9 are all `stage_a_unrecognized`: the fail-closed behaviour of the fail-closed stratum, with no defect in the proof.

**Two definitions to fix before the first review** (report of 2026-10-23 to the project reviewer). Deciding them after seeing the forms would amount to choosing the metric by the result.
1. **Alert unit: declaration or distinct cause?** Per declaration, a single cause in a file becomes dozens or hundreds of alerts (88 in #43841, 412 in #44511). No participant judges 412 declarations one by one, and the rate would be dominated by large files. Per distinct cause (file + reason code + option, when present), the unit is what the participant actually reads and judges.
2. **Does a fail-closed `Não resolvida` count as a false alarm?** In the fail-closed stratum, every alert that is neither a known cause nor a defect is `stage_a_unrecognized`: the tool says "I cannot verify", not "this is wrong". If it counted as a false alarm, the rate in that stratum would be about 9 out of 9 by design, and the kill criterion (> 50 %) would fire by construction.

## 11. Pre-registered metrics (instruction 30, 2026-10-23)

**Pre-registration date:** 2026-10-23. It precedes the sending of the invitation, any reply and any form. This section supersedes the false-alarm definitions of sections 0 and 4 where they differ. Nothing here changes after the data are in; a deviation can only be reported as a deviation, with its reason.

**Freeze:**
- **date:** 2026-10-23;
- **run that generated the alerts:** 39977160187 (`auditor-study`, `study` mode; auditor `ae9f791`; Mathlib `e1b2403b`);
- **commit of the artifacts:** `4feec56`.

Anyone can check that the alerts did not change between the freeze and the analysis: the hashes below are of the content at that commit, and the run keeps the source reports.

**Frozen artifacts** (SHA-256 of the content at commit `4feec56`):

| Artifact | Origin | SHA-256 |
|---|---|---|
| `study/alerts.json` | reports from run 39977160187 (`auditor-study`, `study` mode), auditor `ae9f791`, Mathlib `e1b2403b` | `9d5b8fe308dc31348db45828de43c229c734185932de17bb213146eb91e42761` |
| `study/categories.json` | `study_run.py classify` over the two above | `e4baa167ecba3d8d8dbdf2c7d504dece8ef3eab9bc0157ac2027e091aa984499` |
| `study/defects.json` | ground truth of the defects (checked in run 39977153820) | `a194581230cd7b7d756d480f333403810a8aae09266bf746643d495d73c2ce03` |
| `study/prs.json` | the 10 PRs (mechanical rule of section 2) | `59a642a6d264180724b979c8518166206bfbbf1ce84deea0a2d34580d945e3ac` |
| `study/seed.txt` | seed `1818766798`, published on 2026-10-23 | `07fafe21461fab9fbfb1d0663936bb56fd9986e4c45de2dba09482abdc689d6d` |
| `tools/phase1/study_run.py` | the analysis code (draw, taxonomy, report) | `c4d63260fa6898679b0665000deaae33e31bf5aabf2fe57f9be37cd0703073ff` |

The frozen artifacts are kept byte-for-byte as committed, including the Portuguese text inside them (for example the defect descriptions in `study/defects.json` and the comments in `study_run.py`); translating them would change the hashes.

### 11.1 Alert unit

**Distinct cause:** file + reason code + option, when present (for example `Mathlib/X.lean:set_option_unrecognized:backward.foo`). It is the main metric, because it is what the participant judges. **Affected declarations** are always reported alongside, for transparency: without them, a reader cannot tell whether a cause affects 1 declaration or 412.

### 11.2 Taxonomy (five categories, assigned mechanically)

| # | Category | Declaration | Cause |
|---|---|---|---|
| 1 | Correct verification | `verified`, no real defect | (no cause) |
| 2 | **False alarm** | some reason **asserts** a problem, with no real defect | asserting reason, no real defect |
| 3 | Known cause | all reasons are known causes (section 0) | known-cause reason |
| 4 | Non-coverage | `Não resolvida`/`Não resolvido` due to fail-closed (all other cases), no real defect | reason that does not assert a problem |
| 5 | Correct detection | some reason corresponds to the real defect | reason in `defect_reasons`, in the defect's files |

The rules:
- **An asserting reason** is one whose effect in the aggregator (`src/auditor/aggregator.py`) is `rejected`/`nonconforming`: `*_detected`, `*_reaches_native_eval`, `elaboration_executes_code`, `orphan_justification`, `set_option_violation`, `forbidden_axiom`, `native_decide_unjustified` and `native_decide_justification_malformed`. All other reasons say "I cannot verify".
- **A real defect** is a planted one, per `defect_reasons` in `study/defects.json`, or a defect found by a participant and confirmed by a formal ground truth. In the latter case, it is recorded as a finding, with the proof, and the declaration moves to category 5.
- **Precedence within a declaration:** 1 if `verified`; otherwise 5 if there is a defect reason; otherwise 2 if there is an asserting reason; otherwise 3 if all reasons are known causes; otherwise 4.
- The code is `study_run.classify`, tested in `tests/maintenance/test_phase1_tools.py`.

### 11.3 Formulas

- **False-alarm rate** (criteria of sections 5 and 6) = category 2 / (category 1 + category 2), in **declarations**, **in the success stratum only**.
  - In the fail-closed stratum, category 1 is rare, and the rate is not defined.
  - Category 2 is also reported in causes.
  - The unit is the declaration because category 1 (`verified`) has no cause. **Confirmed by the project reviewer** (instruction 31). The denominator is the set of declarations that the tool evaluated without an alarm (1) or with a false alarm (2). Categories 3 and 4 are left out, because they admit a limitation instead of evaluating.
  - **Both numbers are always reported:** the rate in declarations (the formula) and the count in distinct causes (transparency).
- **Non-coverage rate** = category 4 / all declarations, per stratum, with the number of causes and the time the participant spent on them (column `noncoverage_min`).
- **Main T_net** = T_conventional − (T_assisted − time on known causes), per PR.
  - The result is the **median** over the 10 PRs, also reported per stratum.
  - Time on non-coverage **stays** in T_net: it is a real cost.
- **Secondary T_net** = T_conventional − T_assisted, with known causes included, for transparency.
- **Perceived false alarm:** the causes the participant marked as false (`causes_judged_false`), reported per category and kept separate from the mechanical taxonomy. They measure the participant's reading, not the tool.

### 11.4 Planted defects: the three outcomes

The outcomes apply to the **with**-auditor review of the defect's PR:
- **(a)** the auditor flagged the defect (some declaration in category 5), and the participant gave the verdict `nao_integro` and found the defect;
- **(b)** the auditor flagged it, and the participant approved (`integro` or `nao_sei`). This measures alert noise;
- **(c)** the auditor did not flag it. This is a critical finding and goes into L-32.

In the review **without** the auditor, only whether the participant found the defect is recorded. Outcomes are reported per defect and per condition, never summed.

### 11.5 Criteria (section 5, with instruction 30)

- **Acceptance:** median main T_net > 0 **and** false-alarm rate (success stratum) < 30 %.
- **Kill:** median main T_net < 0 **and** false-alarm rate > 50 %.
- The two criteria are independent: non-coverage weighs on T_net, not on the rate.

### 11.6 What the frozen data already determine (declared before the forms)

Classification of `study/alerts.json` (`study/categories.json`), in declarations and (causes):

| PR | Stratum | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| #45102 | success | 82 | 0 | 1 (1) | 0 | 0 |
| #43841 | success | 0 | 0 | 88 (1) | 0 | 0 |
| #44400 | success | 386 | 0 | 0 | 0 | 55 (2) |
| #45117 | success | 76 | 0 | 1 (1) | 0 | 0 |
| #44973 | success | 88 | 0 | 29 (2) | 0 | 0 |
| #45105 | fail-closed | 0 | 0 | 0 (2) | 248 (1) | 0 |
| #45097 | fail-closed | 227 | 0 | 0 | 203 (3) | 4 (4) |
| #44425 | fail-closed | 0 | 0 | 132 (3) | 43 (2) | 0 |
| #44511 | fail-closed | 222 | 0 | 2 (4) | 412 (3) | 0 |
| #44969 | fail-closed | 90 | 0 | 186 (12) | 17 (1) | 0 |

**Category 2 is zero in every PR.** So the false-alarm rate of the criterion is already determined before any review: **0 / 632 = 0 % in the success stratum**. What the study still measures:
- T_net, main and secondary;
- the non-coverage rate and the time spent on it;
- the outcomes of the planted defects;
- the false alarms **perceived** by the participants.

This is declared here so that it does not later look as if the precision criterion was "passed" by the study: it was fixed by the tool's frozen output.

**Mandatory qualification (instruction 31).** The 0 % of category 2 was fixed by the frozen data, generated before the forms. **It measures the tool within the scope it covers, not in the production configuration**, and it is not a universal property. Any presentation of this result must carry the three qualifications below, in addition to L-26 (self-reviewed classification):
- **Small sample, from one point in time:** 10 PRs (5 in the success stratum), merged into Mathlib between 21 and 22 October 2026 and re-applied on top of `e1b2403b`. It is not an estimate for Mathlib as a whole.
- **"False alarm" here ≠ "false positive" in 1b.** The 28.6 % of 1b (L-31) counted every correct proof that did not come out `verified`. All 10 cases were `Não resolvida` because of a generated `ctorIdx` or of `backward.*`, which in this taxonomy is **category 3**, not 2. Category 2 in 1b was also zero. The number comparable to the 28.6 % is the share of correct declarations that do not come out `verified` in the success stratum: category 3 / (1 + 3) = **119 / 751 = 15.8 %**, from known causes. It is reported alongside.
- **The known causes remain in the sample.** With the per-declaration exclusion (instruction 28), `ctorIdx` and `backward.*` did not leave the sample: they enter as category 3, counted and timed separately. Phase 2, once it fixes these causes, re-measures with the full sample.

*Text suggested by the project reviewer (instruction 31), recorded as received (translated from Portuguese).* "The 0% of category 2 was fixed by the frozen data (alerts generated before the forms) and is a direct consequence of the (B) exclusion: the sample excludes files that fall because of generated `ctorIdx` and `backward.*`, which are the two known causes of false positives in 1b (L-31). The 0% measures the tool within the scope it covers, not in the production configuration. Phase 2, when it fixes these two causes, re-measures with the full sample. Any presentation of this result must declare this qualification."

The adopted text above differs from the suggested one on two facts:
- the per-PR (B) exclusion was replaced by the per-declaration exclusion (instruction 28), and both causes are in the sample;
- both causes produced `Não resolvida` (category 3), not category 2. So excluding them would not explain the 0 % of category 2.

The discrepancy was raised with the project reviewer (report of 2026-10-23).

### 11.7 Criterion × diagnostic (instruction 31)

The false-alarm criterion (< 30 %) applies **only to the mechanical category 2**. The perceived false alarm, i.e. the causes in categories 3 and 4 that participants judged false, is reported as a **diagnostic**, not as a criterion. The distinction exists because the mechanical rate measures a property of the output, while the perceived one measures the participant's experience, which depends on the briefing and on expectations.
- The diagnostic is reported per category, with the reasons given by the participants.
- If a participant judges non-coverage (category 4) a "false alarm", this indicates that the briefing did not explain the difference well. The briefing can be adjusted before the next study, but this does not invalidate the current result.
