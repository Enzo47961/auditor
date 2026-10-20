"""Cenário 02 — `sorry` transitivo: A → B → C → D, sorry em D.

Ground truth: `2 + 2 = 5` é falso (GroundTruth.lean prova a negação).
Q1 (X): admissão transitiva afeta só proof_status."""
from conftest import CONFORMANCE, assert_common_invariants, reasons, run_auditor, state

TARGET = CONFORMANCE / "02-sorry-transitive" / "Fixture" / "A.lean"


def test_02_transitive_sorry_rejected(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    a = r.decl("a_main")
    assert state(a) == ("Rejeitada", "Conforme", "rejected")
    assert "sorryAx_detected" in reasons(a, "proof_status")
    sorry = [x for x in a["admissions"] if x["name"] == "sorryAx"]
    assert sorry and "d_lemma" in sorry[0]["origins"], "origem do sorry deve ser rastreada até D"
    assert r.exit_code == 1


def test_02_only_target_declarations_reported(tmp_path):
    """O relatório cobre as declarações do arquivo-alvo, não as de B, C, D."""
    r = run_auditor(TARGET, tmp_path)
    assert r.report is not None, f"sem relatório (exit={r.exit_code}): {r.stderr}"
    assert {d["declaration_name"] for d in r.report["declarations"]} == {"a_main", "a_clean"}


def test_02_control_validated(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert state(r.decl("a_clean")) == ("Validada", "Conforme", "verified")
