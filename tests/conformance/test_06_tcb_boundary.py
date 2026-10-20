"""Cenário 06 — fronteira de TCB (Q7-a). Canário: `Nat.add` é `@[extern]` do toolchain e
NÃO dispara as regras de implementação nativa. `native_decide` justificado continua
`verified` (05c). Se o Lean mudar onde `Nat.add` vive, ou a fronteira declarada pelo
manifest/toolchain mudar, este cenário falha e a política precisa ser revista (docs/tcb.md).

Ground truth: os dois enunciados são verdadeiros (o kernel os prova sem axiomas)."""
from conftest import CONFORMANCE, assert_common_invariants, run_auditor, state

TARGET = CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean"


def test_06_toolchain_extern_does_not_trigger(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    for n in ("add_native", "add_kernel"):
        d = r.decl(n)
        assert state(d) == ("Validada", "Conforme", "verified"), d["proof_status"]
        assert d["policy_violations"] == []
    assert r.decl("add_native")["justification"] == {"reason": "scenario 06 tcb boundary",
                                                     "reviewer": "@fixture"}
    assert r.exit_code == 0
