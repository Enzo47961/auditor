"""Cenário 04 — `@[implemented_by]`.

Ground truth de (b): a implementação mente; GroundTruth.lean deriva `False`
combinando `f_bad` (native_decide) com a negação provada pelo kernel."""
import pytest

from conftest import (CONFORMANCE, assert_common_invariants, reasons, run_auditor, state,
                      violation_rules)

TARGET = CONFORMANCE / "04-implemented-by" / "Fixture" / "Target.lean"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_auditor(TARGET, tmp_path_factory.mktemp("r04"))


@pytest.mark.parametrize("name", ["g", "f", "g_zero"])
def test_04a_candidate(result, name):
    """`g`, `f`: atributo sozinho. `g_zero`: depende de `g` sem avaliação nativa (Q3a)."""
    assert_common_invariants(result)
    d = result.decl(name)
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    assert "implemented_by_candidate" in reasons(d, "proof_status")


def test_04b_combined_pattern_rejected(result):
    d = result.decl("f_bad")
    assert state(d) == ("Rejeitada", "Conforme", "rejected")   # ofReduceBool justificado
    assert "implemented_by_reaches_native_eval" in reasons(d, "proof_status")
    assert "native_decide_unjustified" not in violation_rules(d)
    assert "implemented_by_reaches_native_eval" in violation_rules(d)
    assert result.exit_code == 1
