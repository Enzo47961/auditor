"""Cenário 03 — axioma DESCONHECIDO em dependência (Q2: reescopado).

`minhaAxioma` não está em nenhuma das duas listas da política default →
premises `Não resolvido`, razão `unknown_axiom` (unknown_axiom_action = fail_closed).
Ground truth: `minhaAxioma : 0 = 1` é falso (GroundTruth.lean prova a negação).
Q1 (X): o kernel aceitou e não há admissão → proof_status `Validada`."""
from conftest import CONFORMANCE, assert_common_invariants, reasons, run_auditor, state

TARGET = CONFORMANCE / "03-axiom-unknown" / "Fixture" / "Target.lean"


def test_03_unknown_axiom_unresolved(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    u = r.decl("usa_axioma")
    assert "minhaAxioma" in {a["name"] for a in u["axioms"]}
    assert state(u) == ("Validada", "Não resolvido", "unresolved")
    assert "unknown_axiom" in reasons(u, "premises_status")
    assert r.exit_code == 1


def test_03_control_validated(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert state(r.decl("nao_usa")) == ("Validada", "Conforme", "verified")
