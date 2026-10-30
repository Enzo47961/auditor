# TCB (Trusted Computing Base) — manifest

Every seal is issued **against an enumerated TCB**. A TCB component is something the seal trusts and that the tool **does not audit**. If any of them is wrong, the seal may be wrong, and the tool has no way of detecting it.

Each report carries the TCB in `tcb` (at the report level and repeated in each declaration). If any mandatory component is missing, no declaration comes out `Validada` (validated): the aggregator applies `tcb_incomplete`, and JSON Schema v1 rejects `Validada` with an incomplete TCB.

## Components

| Field in `tcb` | Component | Identification | Why it is trusted |
|---|---|---|---|
| `kernel` | the Lean kernel | `lean_version`, `githash` (read from Lean itself by the inspector) | It is the anchor: it decides whether a term proves a statement. It is not audited (principle "the kernel is TCB, not an oracle"). |
| `toolchain` | elaborator, compiler, runtime and `lake` of the pinned toolchain | exact `lean_toolchain`; `library_roots` declared by the toolchain | It produces the `.olean` files the inspector reads. With `native_decide`, trust extends to the compiler and the runtime (L-1), and to the toolchain's native implementations (see "TCB boundary"). |
| `dependencies` | Mathlib and other packages | `lake_manifest_sha256`; `packages` (name, type, rev); `project_commit` and `project_dirty` (when the project root is a git repository); `mathlib_commit` (rev of the `mathlib` package, or the project's commit when the project is Mathlib itself) | The dependencies' content is elaborated by the kernel, but the boundary rules and the metadata depend on which packages are present. |
| `inspector` | the Stage B Lean metaprogram (`src/auditor/lean/Inspect.lean`) | `version`, `source_sha256`, `binary_sha256` | It reads the elaborated environment. If it omits a declaration or an axiom, the aggregator does not know. Mitigations in L-14. The binary is compiled per platform, so the hash differs between operating systems. |
| `aggregator` | the Python code of the `auditor` package (Stage A, the Stage B wrapper, policy, aggregator, report) and its Python dependencies | `version`, `source_sha256` (hash of all the package's `.py` files), `python`, `python_dependencies` (installed transitive closure, with exact versions: `jsonschema`, `referencing`, `rpds-py`, `attrs`, …; D-20) | It applies the policy, validates the report against the schema and emits the seal. An unresolvable dependency → incomplete TCB → no `Validada`. |
| `stage_a_parser` | lexical scan and command allow-list | `version`; `allowlist` (kind, toolchain, `env_pin`, generator and classification versions) | It captures what does not exist in the elaborated environment (`set_option`, new syntax, Unicode). |
| `policy` | `policy.toml` | `version`, the file's `sha256` | It defines what is an admission, forbidden, allowed and unknown. |
| `metadata` | transitively imported attributes | count and SHA-256 of the sorted list of `@[simp]`, `@[ext]`, `@[reducible]`, `@[implemented_by]` | Changes to these attributes change the tactics' behaviour; they enter the fingerprint to invalidate seals (principle 7). |
| `fingerprint` | — | SHA-256 of the canonical form (JSON with sorted keys) of all the fields above | It identifies the environment against which the seal was issued. |

**The fingerprint contains no absolute paths**, because it identifies the environment, not the machine. It contains the hash of the inspector binary, which is platform-specific; the same environment on different operating systems produces different fingerprints.

**What is not in the TCB, because it is neither trusted nor checked:** the correspondence between formal and informal statement (always `Não auditada`, not audited), the semantics of proofs, and constructive contexts. These items are listed in `not_covered` and in the seal string.

## TCB boundary

The original specification did not have this section, and two decisions stumbled over its absence:
- **O-1:** the `native_decide` justification accepts trusting the compiler and the runtime.
- **Q7:** the toolchain's own `@[extern]`/`@[implemented_by]` are on the path of almost every proof.

This section closes the gap systematically, not only for Q7.

**Decision (Q7, option a).** Trust is transitive from the kernel and from the dependencies that the toolchain declares. The `@[extern]` and `@[implemented_by]` rules (candidate; combined pattern with `Lean.ofReduceBool`/`Lean.ofReduceNat` → `Rejeitada`, rejected) apply only to **user-level** declarations. **Lean-level** declarations are TCB and do not trigger the rules. A user's `native_decide` still requires a justification; since v4.36 it also never comes out `verified` (Q9-a, L-19). **Measurement confirming Q9-a** (Mathlib `e1b2403b`, `tools/layer2/native_usage.py`): in the `Mathlib` library, 0 proofs use native evaluation (2 of 256,505 declarations are detected by the lexical count, and both are metaprogramming code: the linter that forbids native evaluation and a configuration field). In `MathlibTest`, 33 of 7,463 (0.44 %). The case of the imported tactic (`inclusion +native`, which calls `nativeEqTrue` directly) generates `…._native.inclusion.ax_…` and is caught by the axiom's shape. The impact of Q9-a is confined to `MathlibTest`, where `native_decide` appears legitimately. `Nat.add` (the toolchain's `@[extern]`) triggers nothing (scenario 06).

### (i) The boundary is declared, not inferred from the name

Two sources declare the boundary. The module name never decides, because a user package can have a module called `Init.Something`.

- **The pinned toolchain declares its library roots:** the top-level `.olean` files in `<sysroot>/lib/lean`. On `leanprover/lean4:v4.36.0-rc1` they are `Init`, `Lake`, `LakeMain`, `Lean`, `LeanChecker`, `LeanExport`, `LeanIR`, `Leanc` and `Std` (on v4.22.0 there were six: without `LeanChecker`, `LeanExport` and `LeanIR`).
- **Of the declared roots, only the `target_trusted_roots` are TCB** (D-42, D-47). The file is `src/auditor/data/target_trusted_roots/<toolchain>.json`. **What it means:** the toolchain roots whose modules are implicitly trusted in the target project's closure, i.e. the ones the target uses. **What it does not mean:** "all the roots of Lean's TCB". A root declared by the toolchain and outside this list is still Lean code, but, for the auditor, its modules are treated as user-level: the `@[extern]`/`@[implemented_by]` rules apply (fail-closed).
  - The file is generated by `tools/gen_tcb_roots.py` from the import closure of the Mathlib library at the pinned commit, with the dependencies at the exact revisions of its `lake-manifest.json`. It records the project's commit, the manifest's SHA-256, each package's revision and how many modules of each root the closure uses. The JSON itself carries the `meaning` field with the definition above.
  - At run time, the file must be consistent with the toolchain. If the file for the project's toolchain is missing, if it declares another toolchain, if the list of declared roots recorded in it differs from the sysroot's (drift), or if one of its roots is not declared by the toolchain, the result is `tcb_boundary_undeclared` (exit 2).
  - **Explicit scope** (`v4.36.0-rc1`, Mathlib `e1b2403b`):

    | Root | Declared by Lean v4.36.0-rc1 | Used by Mathlib `e1b2403b` (modules in the closure) | In the auditor's `target_trusted_roots` |
    |---|---|---|---|
    | `Init` | yes | yes (668) | yes |
    | `Lean` | yes | yes (741) | yes |
    | `Std` | yes | yes (215) | yes |
    | `Lake` | yes | yes (1: `Lake.Util.Casing`, via `Mathlib.Tactic.Linter.TextBased`) | yes |
    | `LakeMain` | yes | no | no |
    | `Leanc` | yes | no | no |
    | `LeanChecker` | yes | no | no |
    | `LeanExport` | yes | no | no |
    | `LeanIR` | yes | no | no |

    The last two columns are equal by construction: the file is the measured closure. If a proof starts importing, for example, `LakeMain` (the build tool, not mathematics), that is suspicious, and the auditor treats the module as user-level (fail-closed). A target project other than Mathlib: L-21.
- **`lake-manifest.json` declares the user's packages.** Each package (`git`: `<packagesDir>/<name>`; `path`: `dir`), in addition to the project itself, contributes a user root `<package>/.lake/build/lib/lean`.

The `<sysroot>` is obtained in two independent ways: by the inspector (`findSysroot`, under `lake env`) and by elan (`lean --print-prefix` at the project root). The two must agree; otherwise, `sysroot_mismatch` (exit 2). The inspector's effective search path is also checked: every entry must be the toolchain directory or a root derived from the manifest; otherwise, `search_path_unrecognized` (exit 2).

### Algorithm

Implemented in `src/auditor/tcb_boundary.py`, with unit tests in `tests/tcb/test_boundary.py`.

**Input:**
- the module `M` where the constant with the attribute originates;
- the real path `P` of its `.olean`, resolved through the inspector's effective search path;
- the manifest;
- the sysroot.

**Steps:**
1. If `P` is under a user root and not under `<sysroot>/lib/lean`, the result is **user**.
2. If `P` is under `<sysroot>/lib/lean` and not under a user root, the result is **tcb** only if the three conditions below hold:
   - (a) the root of `M`'s name is declared by the toolchain **and** is in `target_trusted_roots` (otherwise, reason `module_root_not_declared_by_toolchain` or `module_root_not_used_by_target_project`);
   - (b) `P` is exactly `<sysroot>/lib/lean/<M as a path>.olean`;
   - (c) no user root provides an `.olean` for `M` (shadowing).
3. In any other case, the result is **unresolved**: the declaration is `Não resolvida` (unresolved), reason `tcb_boundary_unresolved` (fail-closed).

A manifest with a version outside `1.x`, a package without a name, an unknown package type, a `path` package without `dir`, or a toolchain without declared roots → `tcb_boundary_undeclared` (exit 2).

### (ii) A boundary change requires a policy review

The boundary depends on the pinned toolchain. When bumping `lean-toolchain`:
1. regenerate `target_trusted_roots` (`docs/maintenance.md`, step 8) and run `tests/tcb`, `tests/stage_b` and `tests/conformance/test_06_tcb_boundary.py`. The canary checks the exact list of declared roots, and scenario 06 has one declaration per root of the allow-list, which must come out TCB;
2. if the roots changed, or if a native implementation moved module, the policy must be reviewed by someone other than the author of the change, like any rule change;
3. record the change in `policy.toml`'s history (`policy_version`).

### (iii) The canary: `06-tcb-boundary`

Scenario `tests/conformance/06-tcb-boundary` uses `Nat.add` (an `@[extern]` from `Init.Prelude`) with and without `native_decide`, and requires that no `@[extern]`/`@[implemented_by]` rule fires in either case (without `native_decide`: `verified`; with it: `unresolved` only because of the native auxiliary axiom, Q9-a). Without this test, option (a) would be an untested claim. It fails if:
- Lean changes where `Nat.add` lives;
- Lean stops declaring `Init` as a root;
- the classification starts marking toolchain implementations as user-level or undecidable;
- `target_trusted_roots` stops recognizing a root that Mathlib uses. There is one probe per root:
  `uses_init` (`Nat.add`), `uses_lean` (`Lean.Expr.quickLt`), `uses_std` (`ByteSlice.beq`) and
  `uses_lake` (`Lake.JobTask.toOpaque`, `@[implemented_by]`). The test checks that the roots on the
  list are exactly the probed ones, so a new root without a probe also fails (D-49). The
  mutation "remove root X from `target_trusted_roots`" is detected for each of the four roots.

Case (c) of `04b-extern` tests the opposite side: a lying user `@[extern]`, together with `Nat.add` in the same statement, comes out `Rejeitada`, and only `myF` is flagged.

### Limits of this boundary

- A bug in Lean's runtime or compiler is out of reach. That was already true before Q7 (L-1).
- `@[implemented_by]` in user packages, including Mathlib, still triggers the rules. Its magnitude in Mathlib only shows up in the layer-2 measurements.

## The inspector does not run code from the imported environment (D-39)

Since v4.36, loading the environment's extensions (`importModules (loadExts := true)`) requires `enableInitializersExecution`, which runs the `initialize` blocks of the imported modules — including those of the audited PR — inside the inspector's process. PR code running in the inspector could rewrite the facts it emits. That is why the inspector imports with `loadExts := false` and reads each extension through the entries recorded in each module (`getModuleEntries`), which the import makes available without running anything.

Consequence for `#print axioms`: on v4.36, `Lean.collectAxioms` uses, for imported declarations, precomputed axioms recorded in each `.olean` (`exportedAxiomsExt`). Without the extensions loaded, this table is empty and the algorithm walks the bodies of all constants. The auditor's result therefore does not depend on a summary recorded in the `.olean` by the PR's build. The comparison between the recorded summary and the walk over the bodies is not performed (the state and the extension are private to the `Lean.Util.CollectAxioms` module); see L-20.

The allow-list generator (`Dump.lean`) is the only piece that runs initializers: the modules' command parser only exists with the extensions loaded. It runs during maintenance, on reviewed code (the toolchain's core, or the project at an accepted commit), never on PR code.
