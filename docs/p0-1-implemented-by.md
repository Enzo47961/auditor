# P0-1 — `@[implemented_by]` generated during elaboration (Phase 1, sub-phase 1a.1)

```
status: measurement done (auditor-measure, run 39845428621); 7.35 % of Mathlib's declarations fall only because of a generated ctorIdx → L-34; TCB policy for generated code deferred to Phase 2
```

Classification: `author-self-review` (L-26). "Instruction N" refers to the numbered decisions of the project's external reviewer.

## 1. Mechanism (Lean `v4.36.0-rc1` source, commit `c9afcddf`)

| Generator | Where | What it generates |
|---|---|---|
| `mkCtorIdx` | `Lean/Meta/Constructions/CtorIdx.lean:77–141` | for every inductive with **≥ 2 constructors** that eliminates into `Type`, is not `unsafe`, and is not a runtime type (`Nat`, `Int`…): `T.ctorIdx : T → Nat` (via `casesOn`) with **`@[implemented_by T.ctorIdx._impl]`** (line 139). `_impl` is `unsafe` and equals `getObjTagNat x` (`Init/Prelude.lean:1382`). With 1 constructor: `macroInline`, no attribute |
| `noConfusionType` | `Lean/Meta/Constructions/NoConfusion.lean:103` (and `noConfusionEnum`, 367–418) | uses `T.ctorIdx`; that is why `cases`/injection over an equality of constructors reaches `ctorIdx` |
| `deriving DecidableEq` | `Lean/Elab/Deriving/DecEq.lean:113–154` | compares `ctorIdx` |
| `deriving TypeName` | `Lean/Elab/Deriving/TypeName.lean:25` | `unsafe def instImpl` + **`@[implemented_by instImpl] opaque inst`** (hygienic names) |

The `ctorIdx` of PR #6 (`CategoryTheory.Limits.WalkingParallelPair.ctorIdx`) is the first case. The exact mechanism, which instruction 21 left "to be confirmed", is `mkCtorIdx`, not `deriving DecidableEq`.

## 2. TCB boundary (decision, rule Q7)

- Q7 decides the origin by `lake-manifest.json` and by the toolchain's roots, never by the name.
- The `ctorIdx` of a Mathlib inductive is a constant **of a Mathlib module**. By the rule, the attribute is **user-level**, even though the code that generated it belongs to the toolchain.
- Decision of this sub-phase: **keep it that way**. Whatever reaches a generated `ctorIdx` comes out `implemented_by_candidate` (L-5), never `verified`.
- The same holds for `deriving TypeName` and for project generators (for example, Mathlib's `compile_inductive%`).

**There is no integrity gap**, only a coverage gap:
- Stage A does not see the generated attribute (it is not in the text), but Stage B sees every attribute of the elaborated environment, generated or written.
- No generated `implemented_by` reaches `verified` without being flagged: demonstrated in scenario 08 and in the end-to-end test of the measurement.
- Stage A does not need to be extended to the generation patterns. If it were, it would only repeat, worse (lexically), what Stage B already does in the environment. This corresponds to option (b) of instruction 24, with a caveat: Stage B **already is** the defence. This is recorded here, not as a new limitation.

**Proposal (not applied; the reviewer's decision).** If the measurement shows that the generated `ctorIdx` brings down a large fraction of Mathlib, there is a **structural** recognition that does not depend on the name:
- `T.ctorIdx` with `@[implemented_by T.ctorIdx._impl]`, where `_impl` is `unsafe` and has exactly the body `getObjTagNat` applied, a constant from `Init`;
- and the body of `T.ctorIdx` is the `casesOn` that returns the index of each constructor.

With this, the implementation is the toolchain's (TCB under Q7) and the constant only wraps it. The measurement scanner already checks the first half of this shape (`ctor_idx_shape`). It would be a policy relaxation, with an equivalence test on the pinned toolchain. It is left for after the measurement.

## 3. Regression test (scenario 08)

`tests/conformance/08-generated-implemented-by`. The file does not write `implemented_by`.

| Declaration | Reaches | Required result |
|---|---|---|
| `red_ne_green` (`cases` on `Color.red = Color.green`) | `Color.ctorIdx` (generated) | `unresolved`, `implemented_by_candidate: [Color.ctorIdx]` |
| `idx_red` | `Color.ctorIdx` | same |
| `instTypeNameTag`, `tag_name` | `inst._@…` from `deriving TypeName` | `unresolved`, `implemented_by_candidate` |
| `box_idx` (1 constructor), `plain`, `Color`, `Box` | nothing with the attribute | `verified` (the flagging is not indiscriminate) |

In addition, the test requires that Stage A sees no `implemented_by` and that no declaration with a candidate comes out `verified`. `seg_injective` (`cases` on `Shape.seg a = Shape.seg b`) comes out `verified`: its closure does not go through `Shape.ctorIdx`. This is a measured fact, not a requirement of the test.

## 4. Measurement over the whole of Mathlib

**Tools:**
- `tools/phase1/ImplementedByScan.lean`: runs under `lake env`, imports without extensions (D-39);
- `tools/phase1/implemented_by_measure.py`.

**Steps:**
1. `dump`: every constant of the environment with `implemented_by`/`extern`.
2. `classify`:
   - TCB/user level by the SAME function as the auditor (`tcb_boundary.classify`, Q7);
   - origin `source_written` (the module's source writes `implemented_by X`, lexical scan) or generated, split by generator.
3. `reach`: for each reportable Mathlib declaration (the inspector's criterion), the categories reachable through the same dependency walk as the inspector.

**Check:** `tests/maintenance/test_phase1_tools.py` runs the whole pipeline on scenario 08 and requires it to flag exactly the declarations that the auditor flags.

**Run:** `auditor-measure` in the fork, [run 39845428621](https://github.com/Enzo47961/mathlib4/actions/runs/39845428621).
- Auditor `aa5750b`, fork `afd92f7`; no `.lean` file differs from `e1b2403b`.
- `dump` 3 s, `reach` 43 s, 7.5 GB of RSS. That does not fit on the maintainer's machine (7 GB).
- Data kept outside the repository (maintainer's working directory, `p0/measure1/`).

### 4.1 Constants with a user-level attribute: written × generated

The Mathlib environment has 2046 constants with `implemented_by`/`extern`. 1721 belong to the toolchain (TCB under Q7): 760 `implemented_by` and 961 `extern`. The user-level ones:

| Category | Mathlib | Dependencies | Generator |
|---|---|---|---|
| `source_written` (written in source) | **0** | 20 (Aesop 11, Batteries 7, ProofWidgets 2) | author |
| `generated_ctor_idx` | 186 | 74 (Aesop 42, Batteries 14, importGraph 7, ProofWidgets 5, Qq 4, LeanSearchClient 1, Plausible 1) | Lean, `mkCtorIdx` (`CtorIdx.lean:139`) |
| `generated_other` | 30 | 12 (Aesop 4, Batteries 4, Qq 2, Plausible 2) | Lean, `unsafe e` term (`Lean/Elab/BuiltinNotation.lean:565`: `opaque …unsafe_impl_N` with `implemented_by`), in metaprogramming files |
| `generated_type_name` | 0 | 3 (ProofWidgets) | Lean, `deriving TypeName` |
| `extern_user` | 0 | 0 | — |
| `boundary_unresolved` | 0 | 0 | — |

Mathlib does not write any `implemented_by` in its own source. All of its user-level attributes are generated by Lean. None of the generated ones comes from a generator of the project itself: `compile_inductive%` did not appear as a separate category in this measurement.

### 4.2 Mathlib declarations that fall because of a user-level attribute

Of the **330,852** reportable declarations (the inspector's criterion; includes constructors, projections and instances):

| Reaching | Declarations | % |
|---|---|---|
| any user-level attribute | 24,374 | **7.367 %** |
| only generated attributes | 24,360 | 7.363 % |
| **only a generated `ctorIdx`** | **24,322** | **7.351 %** |
| an attribute written in source (dependencies) | 14 | 0.004 % |
| a generated `unsafe` term | 33 | 0.010 % |
| `deriving TypeName` | 5 | 0.002 % |

**By area**, those that reach a generated `ctorIdx`: `CategoryTheory` 8448, `Algebra` 5083, `AlgebraicGeometry` 4720, `AlgebraicTopology` 1440, `Combinatorics` 682, `RepresentationTheory` 668, `Geometry` 598, `Tactic` 517, `Topology` 376 and others. **It is not an infrastructure effect.** The bulk is category theory and what depends on it: `cases`/`noConfusion` over indexing types such as `WalkingParallelPair`, `WalkingParallelPairHom` and `Pairwise.Hom`.

### 4.3 Conclusion and record

- **> 5 % of declarations** fall only because of a generated attribute. Under instruction 24, this becomes **L-34**: the TCB policy for generated code needs revision in Phase 2.
- **There is no integrity gap.** All of these declarations come out `implemented_by_candidate`, never `verified`.
- **The loss is one of coverage,** and it is concentrated in mathematics.
- The proposal of section 2 (recognizing `ctorIdx` by its shape) would recover 24,322 declarations, 7.35 % of the total. It is left for Phase 2, with an equivalence test (instruction 24).
