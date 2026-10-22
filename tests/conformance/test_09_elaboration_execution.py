"""Cenário 09 — código do usuário executado na elaboração (L-33, emenda L-33a da L-17).

`run_tac` e `by_elab` gravam um marcador no diretório do build: a execução é violação concreta,
`Rejeitada`. A dependência local alterada no PR que executa código deixa o alvo que a importa
`Não resolvida` (`dependency_executes_code`), como o `sorry` transitivo é rastreado até a origem."""
import json
import os
import subprocess
import sys

import pytest

from conftest import CONFORMANCE, DEFAULT_POLICY, ROOT, AuditResult, assert_common_invariants, reasons, \
    run_auditor, state

FIX = CONFORMANCE / "09-elaboration-execution"


def target(name):
    return FIX / "Fixture" / f"{name}.lean"


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("r09")
    return {n: run_auditor(target(n), tmp / n) for n in ("RunTac", "ByElab", "Dep", "Clean", "Uses")}


def run_with_changed(tmp_path, name, changed):
    out = tmp_path / "report.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    cmd = [sys.executable, "-m", "auditor", "check", str(target(name)), "--output", str(out),
           "--policy", str(DEFAULT_POLICY)] + [a for c in changed for a in ("--changed", str(target(c)))]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                       timeout=600)
    return AuditResult(p.returncode, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None,
                       p.stderr)


@pytest.mark.parametrize("name,decls", [("RunTac", ["t", "t2"]), ("ByElab", ["u"]), ("Dep", ["dep_true"])])
def test_execution_in_file_is_rejected(results, name, decls):
    r = results[name]
    assert_common_invariants(r)
    assert r.exit_code == 1
    for n in decls:   # todas as declarações do arquivo, inclusive as que não usam a tática
        d = r.decl(n)
        assert state(d) == ("Rejeitada", "Conforme", "rejected")
        assert "elaboration_executes_code" in reasons(d, "proof_status")
        assert [v["rule"] for v in d["policy_violations"]] == ["elaboration_executes_code"]


def test_control_without_execution_is_verified(results):
    assert state(results["Clean"].decl("clean")) == ("Validada", "Conforme", "verified")
    assert results["Clean"].exit_code == 0


def test_changed_dependency_that_executes_code_makes_target_unresolved(tmp_path):
    r = run_with_changed(tmp_path, "Uses", ["Uses", "Dep", "Clean"])
    d = r.decl("uses")
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    detail = next(x["detail"] for x in d["proof_status"]["reasons"] if x["code"] == "dependency_executes_code")
    assert [m["module"] for m in detail["modules"]] == ["Fixture.Dep"]


def test_without_changed_list_the_dependency_is_not_crossed(results):
    """Limitação declarada (L-33a): sem a lista de alterados, a CLI não cruza dependências; o
    `auditor-ci` sempre passa a lista. O texto do alvo não executa nada."""
    assert state(results["Uses"].decl("uses")) == ("Validada", "Conforme", "verified")


@pytest.fixture(scope="module")
def env_results(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("r09e")
    return {n: run_auditor(target(n), tmp / n) for n in ("Handler", "Extern", "UnsafeCfg")}


@pytest.mark.parametrize("name,decl,constant,reason", [
    ("Handler", "h", "myRfl", "io_type"),
    ("Extern", "e", "myAdd", "extern"),
])
def test_target_defining_executable_code_is_unresolved(env_results, name, decl, constant, reason):
    """Por ambiente: o módulo define código que o elaborador pode executar. Registrar não prova que
    executou: Não resolvida, em todas as declarações do arquivo."""
    d = env_results[name].decl(decl)
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    detail = next(x["detail"] for x in d["proof_status"]["reasons"] if x["code"] == "target_defines_executable_code")
    assert {"name": constant, "reason": reason} in detail["definitions"]


def test_unsafe_in_file_is_unresolved(env_results):
    d = env_results["UnsafeCfg"].decl("v")
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    items = next(x["detail"]["items"] for x in d["proof_status"]["reasons"] if x["code"] == "stage_a_unrecognized")
    assert [i["code"] for i in items] == ["unsafe_code"]


def test_control_file_defines_no_executable_code(results):
    """A detecção por ambiente não dispara em arquivo sem código executável (controle)."""
    assert "target_defines_executable_code" not in reasons(results["Clean"].decl("clean"), "proof_status")
