"""Lacuna A: política ausente, malformada ou com regra inexistente → o auditor não roda.

Unidade (`load_policy`) e fim a fim (CLI: todas as declarações `Não resolvida`,
razão `policy_invalid`, exit 2, sem default silencioso)."""
import pytest

from auditor.policy import PolicyError, load_policy
from conftest import CONFORMANCE, DEFAULT_POLICY, run_auditor

BASE = DEFAULT_POLICY.read_text(encoding="utf-8")


def test_default_policy_loads():
    p = load_policy(DEFAULT_POLICY)
    assert p.version == "1" and p.unknown_axiom_action == "fail_closed"
    assert p.allowed_axioms == {"Classical.choice", "propext", "Quot.sound"}
    assert p.admissions == {"sorryAx"}
    assert p.native_evaluation == {"Lean.ofReduceBool", "Lean.ofReduceNat"}
    assert p.native_attributes == ("implemented_by", "extern") and p.trusted_boundary == "toolchain"
    assert p.exemption_paths == ()                   # isenção de heartbeat: nunca, por default
    assert p.native_auxiliary_action == "fail_closed"


@pytest.mark.parametrize("mutate", [
    lambda s: s + "\n[extra]\nx = 1\n",                                             # tabela desconhecida
    lambda s: s.replace('trusted_boundary = "toolchain"', 'trusted_boundary = "none"'),
    lambda s: s.replace('unknown_axiom_action = "fail_closed"', 'unknown_axiom_action = "ignore"'),
    lambda s: s.replace('unknown_axiom_action = "fail_closed"', 'unknown_axiom_action = "allow_with_warning"'),
    lambda s: s.replace('attributes = ["implemented_by", "extern"]', 'attributes = ["csimp"]'),
    lambda s: s.replace('forbidden = []', 'forbidden = ["propext"]'),               # axioma em 2 listas
    lambda s: s.replace('policy_version = "1"\n', ''),                              # chave obrigatória
    lambda s: s.replace('{ option = "maxHeartbeats", value = "0" }', '{ option = "maxHeartbeats" }'),
    lambda s: s.replace('reason = "test-only heartbeat exemption"', 'reason = ""'),
    lambda s: s.replace('[axioms]', '[axioms'),                                     # TOML inválido
    lambda s: s.replace('native_auxiliary_action = "fail_closed"', 'native_auxiliary_action = "allow"'),
    lambda s: s.replace('native_auxiliary_action = "fail_closed"\n', ''),          # chave obrigatória
    lambda s: s.replace('allowed = ["Classical.choice", "propext", "Quot.sound"]', 'allowed = "propext"'),
])
def test_invalid_policy_rejected(tmp_path, mutate):
    f = tmp_path / "p.toml"
    f.write_text(mutate(BASE), encoding="utf-8")
    with pytest.raises(PolicyError):
        load_policy(f)


def test_missing_policy_rejected(tmp_path):
    with pytest.raises(PolicyError):
        load_policy(tmp_path / "nope.toml")


@pytest.mark.parametrize("content", [None, "isto não é toml = = ="])
def test_cli_policy_invalid_never_defaults(tmp_path, content):
    pol = tmp_path / "policy.toml"
    if content is not None:
        pol.write_text(content, encoding="utf-8")
    r = run_auditor(CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean", tmp_path, policy=pol)
    assert r.exit_code == 2
    assert r.report is not None
    assert [x["code"] for x in r.report["infrastructure"]["reasons"]] == ["policy_invalid"]
    names = {d["declaration_name"] for d in r.report["declarations"]}
    assert names == {"foo", "ok"}
    for d in r.report["declarations"]:
        assert d["proof_status"]["value"] == "Não resolvida"
        assert d["premises_status"]["value"] == "Não resolvido"
        assert {x["code"] for x in d["proof_status"]["reasons"]} == {"policy_invalid"}
