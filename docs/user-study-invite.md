# Invitation to the user study (sub-phase 1c)

```
status: approved (instructions 27, 30 and 31), including the sentence on known causes from instruction 28
```

**Summary.** The text below is sent to the Mathlib community (Zulip, direct contact). It states what instruction 26 requires:
- (a) the classification is self-reviewed (L-26);
- (b) the study measures the tool's value within the scope it covers, not Mathlib coverage;
- (c) alerts from known causes (generated `ctorIdx`, `backward.*`, delaborators/`positivity`) are counted separately, together with the time spent on them (instruction 28; previously: excluded from the sample);
- (d) participation is voluntary, and the estimated time is 2 to 3 hours;
- (e) the result will be published with the qualifications.

The planted defects were approved (instruction 27) and checked with the auditor (runs 39973055204 and 39977153820).

---

**Subject:** Invitation: small user study on a Lean 4 proof-integrity auditor (2–3 hours, voluntary)

Hello,

I maintain an experimental tool that audits the *integrity* of Lean 4 proofs in Mathlib pull requests. For each declaration it reports what the proof actually rests on:
- axioms;
- `sorry`;
- native evaluation (`native_decide`, `implemented_by`, `extern`);
- code executed during elaboration;
- options and commands it cannot classify.

When in doubt, it reports "unresolved" instead of "verified". It does **not** check whether a formal statement matches its informal meaning. It is not a bot: it only comments when a human asks.

I would like to measure, with experienced Mathlib reviewers, whether the tool actually saves reviewing time or adds to it. I am looking for **three Mathlib reviewers**.

**What participation involves**
- About **7 short reviews of real Mathlib pull requests** (replayed on a fixed Mathlib commit), roughly 15–25 minutes each, plus a 15-minute briefing: **about 2–3 hours in total**, at your own pace, over two weeks.
- In some reviews you see the tool's report, in others you do not. The assignment and order are randomized with a published seed.
- For each review you note the start and end time, your verdict on proof integrity, and, when the report is shown, whether any alert looked wrong.
- A few pull requests may contain a deliberately planted integrity defect, each with a formal ground truth. You will not be told which ones.

**What the study measures — and what it does not**
- It measures **the tool's value within the scope it currently covers**. It is **not** a measurement of Mathlib coverage.
- **Some alerts have known causes that are not fixed yet** (see "Known causes of alerts" below). The tool currently reports these cases as "unresolved"; fixing them is planned work. The results will therefore not represent a production configuration, and they will say so.
- **The classification of Mathlib commands used by the tool was written and reviewed by the same author** (`classification_review_status: author-self-review`). There has been no independent review yet.

**Known causes of alerts**
- A few alert types come from known causes that are being fixed (compiler-generated `ctorIdx` implementations; `backward.*` options; delaborators and `positivity` extensions in mathematical files). In some reviews you may see these alerts; if you do, note the time you spend on them separately. They are excluded from the main false-alarm rate and from the main time-saving measurement, and are reported separately.

**Voluntary, and how results are used**
- **Participation is entirely voluntary.** You can stop at any time without giving a reason.
- **Results** will be published in aggregated, anonymized form (reviewer A, B, C) together with the raw anonymized data. Names appear only with explicit consent.
- **Every publication of the results will carry the qualifications above:** self-reviewed classification, covered-scope-only measurement, and the separately reported known-cause alerts.

**Details:** the methodology is public at https://github.com/Enzo47961/auditor/blob/master/docs/user-study.md

If you are willing to take part, or have questions, please reply to this message. Thank you for considering it.

*[Maintainer's name and contact]*
