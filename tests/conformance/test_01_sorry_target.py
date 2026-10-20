"""Cenário 01 — `sorry` no arquivo-alvo.

Ground truth: `foo : 1 = 2` é falso (GroundTruth.lean prova a negação).
Q1 (X): sorryAx é admissão → afeta só proof_status; premissas avaliadas sem ele."""
from conftest import CONFORMANCE, assert_common_invariants, reasons, run_auditor, state

TARGET = CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean"


def test_01_sorry_rejected(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    foo = r.decl("foo")
    assert state(foo) == ("Rejeitada", "Conforme", "rejected")
    assert "sorryAx_detected" in reasons(foo, "proof_status")
    assert any(a["name"] == "sorryAx" for a in foo["admissions"])
    assert r.exit_code == 1


def test_01_control_validated(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    ok = r.decl("ok")
    assert state(ok) == ("Validada", "Conforme", "verified")
    assert ok["admissions"] == [] and ok["axioms"] == []
