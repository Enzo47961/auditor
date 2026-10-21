"""O-3 fim a fim: `maxHeartbeats 0` invalida só a declaração que o usa; a dependente mantém
o próprio estado com `depends_on_rejected`. Opção em nível de arquivo atinge só o que vem
depois dela; opção fora da allow-list é fail-closed."""
import pytest

from conftest import ROOT, assert_common_invariants, reasons, run_auditor, state

TARGET = ROOT / "tests" / "policy" / "set-option" / "Fixture" / "Target.lean"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_auditor(TARGET, tmp_path_factory.mktemp("so"))


def test_invariants(result):
    assert_common_invariants(result)
    assert result.exit_code == 1


@pytest.mark.parametrize("name,expected", [
    ("before_file_opt", ("Validada", "Conforme", "verified")),
    ("heavy", ("Rejeitada", "Conforme", "rejected")),
    ("uses_heavy", ("Validada", "Conforme", "verified")),
    ("fine_opt", ("Validada", "Conforme", "verified")),
    ("unknown_opt", ("Não resolvida", "Conforme", "unresolved")),
    ("unlocked", ("Rejeitada", "Conforme", "rejected")),
    ("after_file_opt", ("Rejeitada", "Conforme", "rejected")),
])
def test_states(result, name, expected):
    assert state(result.decl(name)) == expected


def test_reasons_and_dependency(result):
    assert reasons(result.decl("heavy"), "proof_status") == {"set_option_violation"}
    assert reasons(result.decl("unknown_opt"), "proof_status") == {"set_option_unrecognized"}
    assert result.decl("uses_heavy")["depends_on_rejected"] == ["heavy"]
    v = result.decl("after_file_opt")["policy_violations"]
    assert v[0]["option"] == "autoImplicit" and v[0]["value"] == "true"


def test_unlock_limits_is_the_forbidden_heartbeat_option(result):
    """D-41: `unlock_limits in` cai na mesma regra de `set_option maxHeartbeats 0 in`."""
    d = result.decl("unlocked")
    assert reasons(d, "proof_status") == {"set_option_violation"}
    v = [x for x in d["policy_violations"] if x.get("option") == "maxHeartbeats"]
    assert v and v[0]["value"] == "0"
