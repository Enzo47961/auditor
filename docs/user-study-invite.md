# Convite para o estudo de usuário (sub-fase 1c)

```
status: aprovado pelo revisor do projeto (instrução 27); link conferido (HTTP 200); envio quando os defeitos plantados estiverem prontos
```

**Resumo em português.** O texto abaixo vai em inglês, a língua da comunidade do Mathlib (Zulip, contato direto). Ele declara o que a instrução 26 exige:
- (a) a classificação é auto-revisada (L-26);
- (b) o estudo mede o valor da ferramenta no escopo que ela cobre, não a cobertura do Mathlib;
- (c) a amostra exclui os casos de `ctorIdx` gerado e de `backward.*`;
- (d) a participação é voluntária e o tempo estimado é de 2 a 3 horas;
- (e) o resultado será publicado com a qualificação.

O parágrafo sobre defeitos plantados só fica se a proposta da seção 2 do `user-study.md` for aprovada.

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
- **The sample deliberately excludes two known causes of false alarms:**
  - declarations that reach compiler-generated `ctorIdx` implementations;
  - declarations using `backward.*` options.

  The tool currently reports both as "unresolved"; fixing them is planned work. The results will therefore not represent a production configuration, and they will say so.
- **The classification of Mathlib commands used by the tool was written and reviewed by the same author** (`classification_review_status: author-self-review`). There has been no independent review yet.

**Voluntary, and how results are used**
- **Participation is entirely voluntary.** You can stop at any time without giving a reason.
- **Results** will be published in aggregated, anonymized form (reviewer A, B, C) together with the raw anonymized data. Names appear only with explicit consent.
- **Every publication of the results will carry the qualifications above:** self-reviewed classification, covered-scope-only measurement, and the excluded cases.

**Details:** the methodology is public at https://github.com/Enzo47961/auditor/blob/master/docs/user-study.md

If you are willing to take part, or have questions, please reply to this message. Thank you for considering it.

*[Maintainer's name and contact]*
