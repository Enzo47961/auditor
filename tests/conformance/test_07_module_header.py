"""Cenário 07 — cabeçalho do sistema de módulos (v4.36), como em todo arquivo do Mathlib.

`module` antes de `public import` (D-57) e `refine ⟨?_, ?_⟩` na prova (D-56): nenhum dos dois
pode deixar a declaração `Não resolvida`. Caminho completo Etapa A → Etapa B → política. O
controle com `sorry` confirma que o cabeçalho não desliga a detecção."""
from conftest import CONFORMANCE, assert_common_invariants, reasons, run_auditor, state

TARGET = CONFORMANCE / "07-module-header" / "Fixture" / "Target.lean"


def test_07_module_header_and_synthetic_holes_verified(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    assert_common_invariants(r)
    assert r.report["file_findings"]["unrecognized"] == []
    both = r.decl("both")
    assert state(both) == ("Validada", "Conforme", "verified")
    assert both["admissions"] == [] and both["axioms"] == []
    assert r.report["tcb"]["classification_review_status"] == "core-only"   # L-26: sem allow-list de projeto


def test_07_sorry_still_rejected_under_module_header(tmp_path):
    r = run_auditor(TARGET, tmp_path)
    bad = r.decl("bad")
    assert state(bad) == ("Rejeitada", "Conforme", "rejected")
    assert "sorryAx_detected" in reasons(bad, "proof_status")
    assert r.exit_code == 1
