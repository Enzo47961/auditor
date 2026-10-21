"""auditor-ci (componente 7): orçamento do PR, timeout por arquivo, cache_state, labels.

Critério de aceitação 3 (camada 1): se a auditoria não concluir no orçamento, o resultado é
infraestrutura (exit 2, label `auditor-failed-infra`, o job não falha por isso). Instrução 11:
timeout por arquivo de 90 s que encerra a auditoria do PR (D-21); orçamento wall-clock desde o
trigger, incluindo a preparação; cache `cold` → orçamento estendido, `first_run`,
`cache_cold_extension` e label `auditor-first-run` (D-28). Testado com tempos artificiais; o
tempo real em PRs do Mathlib é evidência da camada 2."""
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from auditor import ci
from conftest import CONFORMANCE, DEFAULT_POLICY, ROOT, require_lake, slow_lean_source

PASS = str(ROOT / "tests" / "ci" / "clean-project" / "Fixture" / "Target.lean")   # tudo verified
FAIL = str(CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean")


def run(tmp_path, files, budget=300.0, extra=()):
    out = tmp_path / "out"
    gh = tmp_path / "gh_output"
    code = ci.main(["run", *files, "--policy", str(DEFAULT_POLICY), "--out-dir", str(out),
                    "--timeout-total", str(budget), "--github-output", str(gh), *extra])
    outcome = json.loads((out / "outcome.json").read_text(encoding="utf-8"))
    return code, outcome, (out / "summary.md").read_text(encoding="utf-8"), gh.read_text(encoding="utf-8")


def test_old_budget_flags_removed(tmp_path):
    """D-36 (instrução 12): `--budget`/`--first-run-budget` viraram `--timeout-total`/
    `--timeout-total-first-run`; os nomes antigos não são aceitos."""
    for old in ("--budget", "--first-run-budget"):
        with pytest.raises(SystemExit):
            ci.main(["run", "--policy", str(DEFAULT_POLICY), "--out-dir", str(tmp_path), old, "5"])


def ago(seconds):
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


def copy_fixture(tmp_path, name, dest):
    proj = tmp_path / dest
    shutil.copytree(CONFORMANCE / name, proj, ignore=shutil.ignore_patterns(".lake"))
    return str(proj / "Fixture" / "Target.lean")


def slow_fixture(tmp_path, dest):
    """Fixture 01 com elaboração lenta (D-58): sozinho, ele compila abaixo do piso de 1 s da Etapa B
    no runner Linux, e o timeout não dispara (falha intermitente no run 39679991017)."""
    target = Path(copy_fixture(tmp_path, "01-sorry-target", dest))
    target.write_text(target.read_text(encoding="utf-8") + slow_lean_source(), encoding="utf-8")
    return str(target)


def test_all_pass(tmp_path):
    """Caminho warm, declarado: o cache do inspetor é aquecido antes (D-58). Sem isso, num runner
    sem cache, o primeiro run sairia `cold` (caminho testado em test_cold_run_*)."""
    require_lake()
    ci._prebuild_inspector(Path(PASS))
    assert ci._inspector_cached(Path(PASS)) is True
    code, o, md, gh = run(tmp_path, [PASS])
    assert code == 0 and o["exit_code"] == 0 and not o["infra_failed"] and not o["audit_failed"]
    assert o["files"][0]["status"] == "pass" and o["files"][0]["counts"] == {"verified": 2}
    assert o["files"][0]["timeout_s"] == ci.DEFAULT_TIMEOUT_FILE_S
    assert o["cache_state"] == "warm" and not o["first_run"] and not o["cache_cold_extension"]
    assert "infra_failed=false" in gh and "audit_failed=false" in gh and "exit_code=0" in gh
    assert "Não Auditada" in md and ci.LABEL not in md and "cache_state: `warm`" in md


def test_rejection_fails_job(tmp_path):
    require_lake()
    code, o, _, gh = run(tmp_path, [PASS, FAIL])
    assert code == 1 and o["audit_failed"] and not o["infra_failed"]
    assert [f["status"] for f in o["files"]] == ["pass", "fail"]
    assert "audit_failed=true" in gh


def test_budget_exhausted_is_infra_exit_2(tmp_path):
    """Orçamento menor que o mínimo: nada é auditado, nada é tratado como sucesso."""
    code, o, md, gh = run(tmp_path, [PASS, FAIL], budget=1.0)
    assert code == 2 and o["exit_code"] == 2
    assert o["infra_failed"] and not o["audit_failed"]
    assert {f["status"] for f in o["files"]} == {"skipped_budget"}
    assert ci.LABEL in md and "Não bloqueia o merge" in md
    assert "infra_failed=true" in gh and "exit_code=2" in gh


def test_setup_time_counts_against_budget(tmp_path):
    """D-28: o relógio começa no trigger; preparação lenta consome o orçamento do steady-state."""
    code, o, _, _ = run(tmp_path, [PASS], extra=["--started-at", ago(400)])
    assert code == 2 and o["files"][0]["status"] == "skipped_budget"
    assert o["clock_origin"] == "trigger" and o["setup_elapsed_s"] >= 400
    assert o["elapsed_s"] >= 400 and not o["cache_cold_extension"]


def test_invalid_clock_falls_back_and_is_declared(tmp_path):
    _, o, _, _ = run(tmp_path, [], extra=["--started-at", "2026-10-20T10:00:00"])   # sem fuso
    assert o["clock_origin"] == "auditor_start_fallback" and o["setup_elapsed_s"] == 0


def test_file_timeout_aborts_the_pr(tmp_path, monkeypatch):
    """D-21: arquivo que estoura o timeout por arquivo encerra a auditoria do PR com exit 2."""
    require_lake()
    first = slow_fixture(tmp_path, "p1")
    monkeypatch.setattr(ci, "MIN_SLICE_S", 0.0)
    code, o, md, _ = run(tmp_path, [first, PASS], extra=["--timeout-file", "0.05"])
    assert code == 2 and o["infra_failed"] and o["timeout_aborted"]
    assert [f["status"] for f in o["files"]] == ["timeout", "not_audited_after_timeout"]
    assert o["files"][0]["timeout_kind"] == "file" and o["files"][0]["timeout_s"] == 0.1
    assert "timeout" in o["files"][0]["infra_reasons"]
    assert "estourou o timeout por arquivo" in md


def test_timeout_by_remaining_budget_is_budget_kind(tmp_path, monkeypatch):
    require_lake()
    first = slow_fixture(tmp_path, "p1")
    monkeypatch.setattr(ci, "MIN_SLICE_S", 0.0)
    code, o, _, _ = run(tmp_path, [first], budget=0.05)
    assert code == 2 and o["files"][0]["status"] == "timeout" and o["files"][0]["timeout_kind"] == "budget"


def test_deleted_and_non_lean_files(tmp_path):
    code, o, md, _ = run(tmp_path, [str(tmp_path / "Removed.lean"), str(tmp_path / "README.md")])
    assert code == 0 and o["files"] == [] and o["deleted_files"] == [str(tmp_path / "Removed.lean")]
    assert "Nenhum arquivo" in md and o["file_duration_p95_s"] is None


def test_inspector_cache_measured(tmp_path):
    require_lake()
    _, o, md, _ = run(tmp_path, [PASS, PASS])
    assert o["files"][1]["inspector_cache"] == "hit" and o["cache_signals"]["inspector"] == "hit"
    assert o["inspector_cache"]["hits"] >= 1 and "cache do inspetor" in md
    assert o["file_duration_p95_s"] == max(f["duration_s"] for f in o["files"])


# ------------------------------------------------------------------ cache_state e first run (D-28)

@pytest.mark.parametrize("build, inspector, state", [
    ("hit", True, "warm"), ("none", True, "warm"), ("none", None, "warm"), ("hit", None, "warm"),
    ("partial", True, "delta"), ("partial", None, "delta"),
    ("miss", True, "cold"), ("miss", None, "cold"), ("hit", False, "cold"), ("none", False, "cold"),
    ("partial", False, "cold"),
])
def test_cache_state(build, inspector, state):
    """`cold` só com evidência positiva; sinal ausente nunca concede orçamento estendido."""
    assert ci.cache_state(build, inspector) == state


def test_cold_run_uses_extended_budget_and_declares_first_run(tmp_path):
    require_lake()
    code, o, md, gh = run(tmp_path, [PASS], extra=["--build-cache", "miss", "--started-at", ago(400)])
    assert code == 0 and o["files"][0]["status"] == "pass"
    assert o["cache_state"] == "cold" and o["first_run"] and o["budget_s"] == ci.DEFAULT_FIRST_RUN_BUDGET_S
    assert o["cache_cold_extension"] and not o["infra_failed"]
    assert ci.LABEL_FIRST_RUN in md and "cache_state=cold" in gh


def test_cold_run_within_steady_state_has_no_extension(tmp_path):
    _, o, _, _ = run(tmp_path, [], extra=["--build-cache", "miss"])
    assert o["first_run"] and not o["cache_cold_extension"]


def test_cold_run_beyond_extended_budget_is_infra(tmp_path):
    code, o, md, _ = run(tmp_path, [PASS], extra=["--build-cache", "miss", "--started-at", ago(1000)])
    assert code == 2 and o["infra_failed"] and not o["cache_cold_extension"]
    assert ci.LABEL in md and ci.LABEL_FIRST_RUN not in md


def test_partial_cache_is_delta_with_steady_state_budget(tmp_path):
    code, o, _, _ = run(tmp_path, [PASS], extra=["--build-cache", "partial", "--started-at", ago(400)])
    assert o["cache_state"] == "delta" and o["budget_s"] == 300.0 and code == 2


# ------------------------------------------------------------------ decisão do label (workflow confiável)

def _outcome(tmp_path, data):
    p = tmp_path / "outcome.json"
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return p


GOOD = {"schema": ci.OUTCOME_SCHEMA, "infra_failed": False, "cache_cold_extension": False}


@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out", "skipped", "action_required", "neutral"])
def test_label_when_job_did_not_conclude(tmp_path, conclusion):
    assert ci.label_decision(_outcome(tmp_path, GOOD), conclusion)[0] == ci.LABEL


@pytest.mark.parametrize("data", [
    "não é json", [], {"infra_failed": False, "cache_cold_extension": False},       # sem schema
    {**GOOD, "infra_failed": "false"},                                             # tipo errado
    {**GOOD, "cache_cold_extension": 0},
    {"schema": ci.OUTCOME_SCHEMA, "cache_cold_extension": False},                  # campo ausente
    {"schema": ci.OUTCOME_SCHEMA, "infra_failed": False},
    {**GOOD, "schema": "auditor-ci-outcome/1"},                                    # versão anterior
    {**GOOD, "infra_failed": True},
    {**GOOD, "infra_failed": True, "cache_cold_extension": True},                  # infra vence
])
def test_label_fail_closed_on_bad_or_infra_outcome(tmp_path, data):
    assert ci.label_decision(_outcome(tmp_path, data), "success")[0] == ci.LABEL


def test_label_when_outcome_missing(tmp_path):
    assert ci.label_decision(tmp_path / "nope.json", "failure")[0] == ci.LABEL
    assert ci.label_decision(None, "success")[0] == ci.LABEL


def test_first_run_label_only_for_cold_extension(tmp_path):
    p = _outcome(tmp_path, {**GOOD, "cache_cold_extension": True})
    assert ci.label_decision(p, "success")[0] == ci.LABEL_FIRST_RUN


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_no_label_for_clean_outcome(tmp_path, conclusion):
    """`failure` com outcome limpo = rejeição real; o job falhou, mas não é infraestrutura."""
    assert ci.label_decision(_outcome(tmp_path, GOOD), conclusion)[0] is None


def test_label_decision_cli_writes_output(tmp_path):
    gh = tmp_path / "gh"
    assert ci.main(["label-decision", "--conclusion", "cancelled", "--github-output", str(gh)]) == 0
    assert gh.read_text(encoding="utf-8") == f"label={ci.LABEL}\n"
    gh2 = tmp_path / "gh2"
    ok = _outcome(tmp_path, GOOD)
    assert ci.main(["label-decision", "--outcome", str(ok), "--conclusion", "success",
                    "--github-output", str(gh2)]) == 0
    assert gh2.read_text(encoding="utf-8") == "label=\n"


# ------------------------------------------------------------------ comentário pedido por humano

def test_comment_declares_human_request_and_truncates():
    body = ci.comment_body("x" * (ci.COMMENT_LIMIT + 10), "a" * 40)
    assert body.startswith("Pedido por um humano (`@auditor report`)")
    assert len(body) < ci.COMMENT_LIMIT + 200 and "truncado" in body


def test_p95():
    assert ci._p95([]) is None
    assert ci._p95([3.0]) == 3.0
    assert ci._p95([float(i) for i in range(1, 21)]) == 19.0
    assert ci._p95([float(i) for i in range(1, 101)]) == 95.0


# ------------------------------------------------------------------ precedência no nível do PR (sem Lean)

def fake_children(monkeypatch, behaviours):
    """Substitui o subprocesso por respostas fixas: exit code (grava relatório) ou 'timeout'."""
    import subprocess as sp
    calls = iter(behaviours)

    def fake_run(cmd, **kw):
        b = next(calls)
        if b == "timeout":
            raise sp.TimeoutExpired(cmd, kw["timeout"])
        out = cmd[cmd.index("--output") + 1]
        status = {0: "verified", 1: "rejected", 2: "unresolved"}[b]
        reasons = [{"code": "compile_failure"}] if b == 2 else []
        with open(out, "w", encoding="utf-8") as fh:
            json.dump({"declarations": [{"overall_status": status}], "infrastructure": {"reasons": reasons}}, fh)
        return sp.CompletedProcess(cmd, b, "", "")

    monkeypatch.setattr(ci.subprocess, "run", fake_run)
    monkeypatch.setattr(ci, "_inspector_cached", lambda p: None)


def lean_files(tmp_path, n):
    fs = []
    for i in range(n):
        f = tmp_path / f"F{i}.lean"
        f.write_text("theorem t : True := trivial\n", encoding="utf-8")
        fs.append(str(f))
    return fs


def test_infra_outranks_rejection_but_rejection_still_fails_job(tmp_path, monkeypatch):
    fake_children(monkeypatch, [1, "timeout"])
    code, o, md, gh = run(tmp_path, lean_files(tmp_path, 3))
    assert code == 2 and o["exit_code"] == 2
    assert o["audit_failed"] and o["infra_failed"]          # o job ainda falha pela rejeição (D-22)
    assert [f["status"] for f in o["files"]] == ["fail", "timeout", "not_audited_after_timeout"]
    assert "audit_failed=true" in gh and ci.LABEL in md


def test_child_exit_2_is_infra_without_abort(tmp_path, monkeypatch):
    fake_children(monkeypatch, [2, 0])
    code, o, _, _ = run(tmp_path, lean_files(tmp_path, 2))
    assert code == 2 and [f["status"] for f in o["files"]] == ["infra", "pass"] and not o["timeout_aborted"]
