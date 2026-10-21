"""Cenário 06 — fronteira de TCB (Q7-a). Canário: `Nat.add` é `@[extern]` do toolchain e
NÃO dispara as regras de implementação nativa. Na v4.36, `add_native` sai `unresolved` só pelo
axioma auxiliar nativo (`native_auxiliary_axiom`, Q9-a; na v4.22 era `verified`); o
canário continua sendo que nenhuma regra de `extern`/`implemented_by` é disparada. Se o Lean mudar onde `Nat.add` vive, ou a fronteira declarada pelo
manifest/toolchain mudar, este cenário falha e a política precisa ser revista (docs/tcb.md).

Ground truth: os dois enunciados são verdadeiros (o kernel os prova sem axiomas)."""
from conftest import CONFORMANCE, assert_common_invariants, run_auditor, state

TARGET = CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean"


def test_06_toolchain_extern_does_not_trigger(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    k = r.decl("add_kernel")
    assert state(k) == ("Validada", "Conforme", "verified"), k["proof_status"]
    n = r.decl("add_native")
    assert state(n) == ("Validada", "Não resolvido", "unresolved"), n["premises_status"]
    for d in (k, n):
        assert d["policy_violations"] == []
        codes = {x["code"] for s in ("proof_status", "premises_status") for x in d[s]["reasons"]}
        assert not codes & {"extern_candidate", "extern_reaches_native_eval", "implemented_by_candidate",
                            "implemented_by_reaches_native_eval", "tcb_boundary_unresolved"}, codes
    assert {x["code"] for x in n["premises_status"]["reasons"]} == {"native_auxiliary_axiom"}
    assert n["justification"] == {"reason": "scenario 06 tcb boundary", "reviewer": "@fixture"}
    assert r.exit_code == 1


ROOT_PROBES = {"Init": "uses_init", "Lean": "uses_lean", "Std": "uses_std", "Lake": "uses_lake"}


def test_06_one_probe_per_allowlisted_root(tmp_path):
    """Drift da D-42 (D-49): cada raiz da allow-list tem uma declaração que usa uma constante
    `@[extern]`/`@[implemented_by]` daquela raiz. Se a allow-list deixar de reconhecer a raiz,
    a declaração sai `unresolved` (`tcb_boundary_unresolved`) e este teste falha."""
    from auditor import tcb_boundary as tb
    assert set(tb.load_tcb_roots("leanprover/lean4:v4.36.0-rc1")["roots"]) == set(ROOT_PROBES)
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    for root, name in ROOT_PROBES.items():
        d = r.decl(name)
        assert state(d) == ("Validada", "Conforme", "verified"), (root, d["premises_status"])
        codes = {x["code"] for s in ("proof_status", "premises_status") for x in d[s]["reasons"]}
        assert not codes & {"tcb_boundary_unresolved", "extern_candidate", "implemented_by_candidate"}, codes
