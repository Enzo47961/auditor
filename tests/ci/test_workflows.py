"""Política dos workflows como teste (componente 7, princípio 8, D-24).

* nenhum `pull_request_target` (rodaria código do PR com token de escrita);
* o job que roda código do PR só tem permissão de leitura e não persiste credenciais;
* os workflows com permissão de escrita (label, comentário) nunca fazem checkout;
* comentário só com pedido humano explícito (`@auditor report`) de quem tem acesso;
* nenhum texto controlado pelo autor do PR interpolado com `${{ }}` dentro de `run:`;
* ações fixadas por SHA de commit (D-25); elan da release fixada, com SHA-256 conferido."""
import re
from pathlib import Path

import pytest
import yaml

from conftest import ROOT

WF = ROOT / ".github" / "workflows"
TPL = ROOT / "ci" / "templates"
ALL = sorted([*WF.glob("*.yml"), *TPL.glob("*.yml")])
UNTRUSTED = re.compile(r"\$\{\{\s*github\.(event\.(pull_request\.(title|body|head\.ref|head\.label)|"
                       r"comment\.body|issue\.(title|body)|review\.body|head_commit\.message)|head_ref)")


def load(p: Path) -> dict:
    d = yaml.safe_load(p.read_text(encoding="utf-8"))
    d["on"] = d.pop(True, d.get("on"))      # YAML 1.1 lê `on:` como True
    return d


def steps(d: dict) -> list[dict]:
    return [s for j in d["jobs"].values() for s in j.get("steps", [])]


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.name)
def test_never_pull_request_target(p):
    assert "pull_request_target" not in p.read_text(encoding="utf-8")


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.name)
def test_no_untrusted_interpolation_in_scripts(p):
    for s in steps(load(p)):
        assert not UNTRUSTED.search(s.get("run", "")), (p.name, s.get("name"))


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.name)
def test_actions_pinned_to_commit_sha(p):
    """D-25 (instrução 11): obrigatório. Tag é mutável; SHA de commit não. A versão legível fica
    num comentário `# vX.Y.Z` na mesma linha, para a revisão da atualização."""
    for s in steps(load(p)):
        if "uses" in s:
            assert re.search(r"@[0-9a-f]{40}$", s["uses"]), s["uses"]
    for line in p.read_text(encoding="utf-8").splitlines():
        if re.match(r"\s*(-\s+)?uses:\s+actions/", line):
            assert re.search(r"@[0-9a-f]{40} # v\d+\.\d+\.\d+$", line), line
    for j in load(p)["jobs"].values():
        if "uses" in j:     # chamada de workflow reutilizável: SHA fixado (placeholder no modelo)
            assert j["uses"].endswith("@AUDITOR_SHA") or re.search(r"@[0-9a-f]{40}$", j["uses"])


@pytest.mark.parametrize("p", [WF / "ci.yml", WF / "auditor-tier1.yml"], ids=lambda p: p.name)
def test_elan_release_pinned_and_hash_checked(p):
    """O elan-init.sh baixa a release `latest` do elan: fixar a tag do script não fixa o elan.
    Os workflows baixam o binário da release fixada e conferem o SHA-256."""
    step = [s for s in steps(load(p)) if "elan" in s.get("name", "")][0]
    assert "elan-init.sh" not in step["run"] and "latest" not in step["run"]
    assert step["env"]["ELAN_VERSION"] == "v4.2.4"
    assert re.fullmatch(r"[0-9a-f]{64}", step["env"]["ELAN_SHA256"])
    assert 'sha256sum -c -' in step["run"]
    assert step["run"].index("sha256sum -c -") < step["run"].index("elan-init\" -y")


@pytest.mark.parametrize("p", ALL, ids=lambda p: p.name)
def test_top_level_permissions_read_only(p):
    assert load(p)["permissions"] == {"contents": "read"}


def test_audit_job_is_read_only_and_does_not_persist_credentials():
    d = load(WF / "auditor-tier1.yml")
    assert list(d["on"]) == ["workflow_call"]
    job = d["jobs"]["audit"]
    assert job["permissions"] == {"contents": "read"}
    for s in job["steps"]:
        if s.get("uses", "").startswith("actions/checkout"):
            assert s["with"]["persist-credentials"] is False
    names = [s.get("name", s.get("uses")) for s in job["steps"]]
    assert "artefato com os relatórios completos" in names
    upload = [s for s in job["steps"] if s.get("uses", "").startswith("actions/upload-artifact")][0]
    assert upload["if"] == "always()" and upload["with"]["name"] == "auditor-report"
    run_step = [s for s in job["steps"] if s.get("id") == "audit"][0]
    assert "--budget" in run_step["run"] and "$GITHUB_STEP_SUMMARY" in run_step["run"]


def test_audit_step_budget_clock_cache_and_job_result():
    """Instrução 11: timeout por arquivo, relógio desde o trigger, cache_state; o job falha só por
    rejeição (D-22), não por infraestrutura (exit 2)."""
    d = load(WF / "auditor-tier1.yml")
    inputs = d["on"]["workflow_call"]["inputs"]
    assert inputs["budget-seconds"]["default"] == 300 and inputs["first-run-budget-seconds"]["default"] == 900
    assert inputs["timeout-file-seconds"]["default"] == 90
    job = d["jobs"]["audit"]
    names = [s.get("id") for s in job["steps"]]
    assert names.index("clock") == 0                         # relógio antes de qualquer preparação
    run_step = [s for s in job["steps"] if s.get("id") == "audit"][0]
    for flag in ("--timeout-file", "--first-run-budget", "--build-cache", "--started-at", "--started-at-kind"):
        assert flag in run_step["run"]
    assert "|| rc=$?" in run_step["run"]                     # exit 2 não falha o passo
    assert run_step["env"]["TRIGGER_AT"] == "${{ github.event.pull_request.updated_at }}"
    fail = [s for s in job["steps"] if s.get("name") == "rejeição falha o job (D-22)"][0]
    assert fail["if"] == "steps.audit.outputs.audit_failed == 'true'" and "exit 1" in fail["run"]
    cache_idx = names.index("mathlib-cache")
    get_idx = [s.get("name") for s in job["steps"]].index("cache de build do Mathlib")
    assert cache_idx < get_idx < names.index("audit")       # cache get dentro do relógio do PR


def test_audit_job_never_comments_or_labels():
    text = (WF / "auditor-tier1.yml").read_text(encoding="utf-8")
    assert "gh pr comment" not in text and "add-label" not in text


@pytest.mark.parametrize("name", ["auditor-label.yml", "auditor-report.yml"])
def test_write_workflows_never_checkout(name):
    d = load(TPL / name)
    for s in steps(d):
        assert not s.get("uses", "").startswith("actions/checkout"), s
    perms = [j["permissions"] for j in d["jobs"].values()]
    assert all("contents" not in p or p["contents"] == "read" for p in perms)


def test_label_workflow_is_trusted_trigger_and_fail_closed():
    d = load(TPL / "auditor-label.yml")
    assert list(d["on"]) == ["workflow_run"] and d["on"]["workflow_run"]["workflows"] == ["auditor-tier1"]
    text = (TPL / "auditor-label.yml").read_text(encoding="utf-8")
    assert "auditor-ci label-decision" in text and "auditor-failed-infra" in text
    dl = [s for s in steps(d) if s.get("uses", "").startswith("actions/download-artifact")][0]
    assert dl["continue-on-error"] is True       # artefato ausente → decisão fail-closed, não erro
    apply = [s for s in steps(d) if s.get("name") == "aplicar o label"][0]
    assert apply["env"]["LABEL"] == "${{ steps.decide.outputs.label }}"     # via env, não interpolado
    assert "${{" not in apply["run"]
    assert "auditor-failed-infra)" in apply["run"] and "auditor-first-run)" in apply["run"]
    assert '*) echo "label inesperado' in apply["run"]                      # só os dois labels conhecidos


def test_report_workflow_requires_explicit_human_request():
    d = load(TPL / "auditor-report.yml")
    assert list(d["on"]) == ["issue_comment"]
    cond = d["jobs"]["report"]["if"]
    assert "startsWith(github.event.comment.body, '@auditor report')" in cond
    assert "author_association" in cond and "github.event.issue.pull_request" in cond


def test_caller_template_runs_only_on_lean_changes():
    d = load(TPL / "auditor-tier1.yml")
    assert d["on"]["pull_request"]["paths"] == ["**.lean"]
