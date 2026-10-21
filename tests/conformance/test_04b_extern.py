"""Cenário 04b — `@[extern]` (O-5), análogo ao 04; regras só para user-level (Q7-a).

Ground truth de (b) e (c): o código nativo de `myF` soma, a definição multiplica;
GroundTruth.lean deriva `False` com a negação provada pelo kernel sem axiomas."""
import pytest

from conftest import (CONFORMANCE, assert_common_invariants, reasons, run_auditor, state,
                      violation_rules)

TARGET = CONFORMANCE / "04b-extern" / "Fixture" / "Target.lean"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_auditor(TARGET, tmp_path_factory.mktemp("r04b"))


@pytest.mark.parametrize("name", ["h", "h_zero", "e_zero"])
def test_04b_a_candidate(result, name):
    assert_common_invariants(result)
    d = result.decl(name)
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    assert "extern_candidate" in reasons(d, "proof_status")


@pytest.mark.parametrize("name", ["e_bad", "e_mixed"])
def test_04b_bc_combined_pattern_rejected(result, name):
    d = result.decl(name)
    # justificado; premissas `Não resolvido` pelo axioma auxiliar nativo (v4.36, Q9-a)
    assert state(d) == ("Rejeitada", "Não resolvido", "rejected")
    assert "native_auxiliary_axiom" in reasons(d, "premises_status")
    assert "extern_reaches_native_eval" in reasons(d, "proof_status")
    assert "native_decide_unjustified" not in violation_rules(d)
    assert result.exit_code == 1


def test_04b_c_toolchain_extern_not_flagged(result):
    """(c): `Nat.add` (toolchain) está no mesmo enunciado; só `myF` é apontado."""
    d = result.decl("e_mixed")
    v = [x for x in d["policy_violations"] if x["rule"] == "extern_reaches_native_eval"]
    assert v and v[0]["constants"] == ["myF"]
    flagged = {c for r in d["proof_status"]["reasons"] for c in r["detail"].get("constants", [])}
    assert flagged == {"myF"}
