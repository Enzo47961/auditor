"""Cenário 05 — `native_decide` e gramática estrita da justificativa (O-1, opção B).

Q1 (X): avaliação nativa sem justificativa válida afeta premises (`Não conforme`);
proof_status permanece `Validada` (kernel aceitou, sem admissão).

v4.36.0-rc1: o `native_decide` não usa mais `Lean.ofReduceBool`; adiciona, por uso, o axioma
auxiliar `<dona>._native.native_decide.ax_1_1` : `e = true`, que o kernel não reconfere.
As regras de justificativa valem para ele; além delas, o axioma auxiliar deixa as premissas
`Não resolvido` (`native_auxiliary_axiom`) até a decisão da Q9. Consequência: o caso
justificado (05c, 05f) passou de `verified` para `unresolved`; nenhum outro resultado mudou.
Ground truth: `#print axioms` confirma o axioma auxiliar em cada declaração com native_decide
e sua ausência em `drift_holder` (GroundTruth.lean)."""
import pytest

from conftest import (CONFORMANCE, assert_common_invariants, reasons, run_auditor, state,
                      violation_rules)

TARGET = CONFORMANCE / "05-native-decide" / "Fixture" / "Target.lean"
UNJUSTIFIED = ("Validada", "Não conforme", "rejected")
JUSTIFIED_Q9 = ("Validada", "Não resolvido", "unresolved")    # v4.22: ("Validada", "Conforme", "verified")


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_auditor(TARGET, tmp_path_factory.mktemp("r05"))


def test_05_invariants(result):
    assert_common_invariants(result)
    assert result.exit_code == 1


@pytest.mark.parametrize("name", ["nd_nodoc", "nd_plain_doc"])
def test_05a_b_unjustified(result, name):
    d = result.decl(name)
    assert state(d) == UNJUSTIFIED
    assert "native_decide_unjustified" in reasons(d, "premises_status")
    assert "native_decide_unjustified" in violation_rules(d)


def test_05c_justified(result):
    d = result.decl("nd_justified")
    assert state(d) == JUSTIFIED_Q9
    assert reasons(d, "premises_status") == {"native_auxiliary_axiom"}
    assert d["justification"] == {"reason": "kernel decide too slow", "reviewer": "@enzo"}
    assert d["policy_violations"] == []


def test_05d_drift_victim(result):
    """Drift multi-declaração: justificativa na vizinha não cobre quem usa native_decide."""
    d = result.decl("drift_victim")
    assert state(d) == UNJUSTIFIED
    assert "native_decide_unjustified" in violation_rules(d)


def test_05d_drift_holder_orphan(result):
    """Q3b: justificativa órfã é violação (fail-closed). Violação de política que não é
    sobre dependência → proof_status `Rejeitada` (definição da spec + Q1 X)."""
    d = result.decl("drift_holder")
    assert state(d) == ("Rejeitada", "Conforme", "rejected")
    assert "orphan_justification" in reasons(d, "proof_status")
    assert "orphan_justification" in violation_rules(d)


@pytest.mark.parametrize("name", ["bad_multiline", "bad_escape", "bad_no_reviewer",
                                  "bad_handle", "bad_duplicate"])
def test_05e_malformed(result, name):
    d = result.decl(name)
    assert state(d) == UNJUSTIFIED
    assert "native_decide_justification_malformed" in reasons(d, "premises_status")
    assert "native_decide_justification_malformed" in violation_rules(d)


def test_05f_consumer_of_justified(result):
    d = result.decl("consumes_justified")
    assert state(d) == JUSTIFIED_Q9
    assert reasons(d, "premises_status") == {"native_auxiliary_axiom"}


def test_05f_consumer_of_unjustified_attributed_to_owner(result):
    d = result.decl("consumes_unjustified")
    assert state(d) == UNJUSTIFIED
    vs = [v for v in d["policy_violations"] if v["rule"] == "native_decide_unjustified"]
    assert vs and vs[0]["owner"] == "nd_nodoc"
