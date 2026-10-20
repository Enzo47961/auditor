"""auditor-ci (componente 7): orçamento de 5 min, label `auditor-failed-infra`, não bloqueio.

Critério de aceitação 3 (camada 1): se a auditoria não concluir no orçamento, o resultado é
`infra_failed` (label) e o comando sai com 0 (não bloqueia merge). Testado com orçamento
artificial; o tempo real em PRs do Mathlib é evidência da camada 2."""
import json
import shutil

import pytest

from auditor import ci
from conftest import CONFORMANCE, DEFAULT_POLICY, require_lake

PASS = str(CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean")
FAIL = str(CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean")


def run(tmp_path, files, budget=300.0, extra=()):
    out = tmp_path / "out"
    gh = tmp_path / "gh_output"
    code = ci.main(["run", *files, "--policy", str(DEFAULT_POLICY), "--out-dir", str(out),
                    "--budget", str(budget), "--github-output", str(gh), *extra])
    outcome = json.loads((out / "outcome.json").read_text(encoding="utf-8"))
    return code, outcome, (out / "summary.md").read_text(encoding="utf-8"), gh.read_text(encoding="utf-8")


def test_all_pass(tmp_path):
    require_lake()
    code, o, md, gh = run(tmp_path, [PASS])
    assert code == 0 and not o["infra_failed"] and not o["audit_failed"]
    assert o["files"][0]["status"] == "pass" and o["files"][0]["counts"] == {"verified": 2}
    assert "infra_failed=false" in gh and "audit_failed=false" in gh
    assert "Não Auditada" in md and ci.LABEL not in md


def test_rejection_fails_job(tmp_path):
    require_lake()
    code, o, _, _ = run(tmp_path, [PASS, FAIL])
    assert code == 1 and o["audit_failed"] and not o["infra_failed"]
    assert [f["status"] for f in o["files"]] == ["pass", "fail"]


def test_budget_exhausted_is_infra_and_does_not_block(tmp_path):
    """Orçamento menor que o mínimo: nada é auditado, nada é tratado como sucesso."""
    code, o, md, gh = run(tmp_path, [PASS, FAIL], budget=1.0)
    assert code == 0
    assert o["infra_failed"] and not o["audit_failed"]
    assert {f["status"] for f in o["files"]} == {"skipped_budget"}
    assert ci.LABEL in md and "Não bloqueia o merge" in md
    assert "infra_failed=true" in gh


def test_timeout_inside_audit_is_infra_and_does_not_block(tmp_path, monkeypatch):
    """O auditor recebe o restante do orçamento como timeout; estourá-lo é infraestrutura."""
    require_lake()
    proj = tmp_path / "p"
    shutil.copytree(CONFORMANCE / "01-sorry-target", proj, ignore=shutil.ignore_patterns(".lake"))
    monkeypatch.setattr(ci, "MIN_SLICE_S", 0.0)
    code, o, md, _ = run(tmp_path, [str(proj / "Fixture" / "Target.lean")], budget=0.05)
    assert code == 0 and o["infra_failed"]
    assert o["files"][0]["status"] == "infra" and "timeout" in o["files"][0]["infra_reasons"]


def test_deleted_and_non_lean_files(tmp_path):
    code, o, md, _ = run(tmp_path, [str(tmp_path / "Removed.lean"), str(tmp_path / "README.md")])
    assert code == 0 and o["files"] == [] and o["deleted_files"] == [str(tmp_path / "Removed.lean")]
    assert "Nenhum arquivo" in md


def test_inspector_cache_measured(tmp_path):
    require_lake()
    _, o, md, _ = run(tmp_path, [PASS, PASS])
    assert o["files"][1]["inspector_cache"] == "hit"
    assert o["inspector_cache"]["hits"] >= 1 and "cache do inspetor" in md


# ------------------------------------------------------------------ decisão do label (workflow confiável)

def _outcome(tmp_path, data):
    p = tmp_path / "outcome.json"
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


GOOD = {"schema": ci.OUTCOME_SCHEMA, "infra_failed": False}


@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out", "skipped", "action_required", "neutral"])
def test_label_when_job_did_not_conclude(tmp_path, conclusion):
    assert ci.label_decision(_outcome(tmp_path, GOOD), conclusion)[0] is True


@pytest.mark.parametrize("data", [
    "não é json", [], {"infra_failed": False},                                     # sem schema
    {"schema": ci.OUTCOME_SCHEMA, "infra_failed": "false"},                        # tipo errado
    {"schema": ci.OUTCOME_SCHEMA},                                                 # campo ausente
    {"schema": "outro/1", "infra_failed": False},
    {"schema": ci.OUTCOME_SCHEMA, "infra_failed": True},
])
def test_label_fail_closed_on_bad_or_infra_outcome(tmp_path, data):
    assert ci.label_decision(_outcome(tmp_path, data), "success")[0] is True


def test_label_when_outcome_missing(tmp_path):
    assert ci.label_decision(tmp_path / "nope.json", "failure")[0] is True
    assert ci.label_decision(None, "success")[0] is True


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_no_label_for_clean_outcome(tmp_path, conclusion):
    """`failure` com outcome limpo = rejeição real; o job falhou, mas não é infraestrutura."""
    assert ci.label_decision(_outcome(tmp_path, GOOD), conclusion)[0] is False


def test_label_decision_cli_writes_output(tmp_path):
    gh = tmp_path / "gh"
    assert ci.main(["label-decision", "--conclusion", "cancelled", "--github-output", str(gh)]) == 0
    assert gh.read_text(encoding="utf-8") == "label=true\n"


# ------------------------------------------------------------------ comentário pedido por humano

def test_comment_declares_human_request_and_truncates():
    body = ci.comment_body("x" * (ci.COMMENT_LIMIT + 10), "a" * 40)
    assert body.startswith("Pedido por um humano (`@auditor report`)")
    assert len(body) < ci.COMMENT_LIMIT + 200 and "truncado" in body
