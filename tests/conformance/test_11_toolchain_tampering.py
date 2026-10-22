"""Cenário 11 — L-33 (b): adulteração do auditor ou do inspetor durante o build do alvo.

(a) defende contra execução (`run_tac` sai Rejeitada); (b) defende contra adulteração: se o build
altera o inspetor ou o pacote do auditor, o inspetor não roda e o arquivo sai `Não resolvida`
(`toolchain_tampered`). Cada teste usa uma cópia do projeto (build novo, sem `.olean` em cache) e
uma cópia do pacote do auditor ou um cache próprio do inspetor: nada do repositório é alterado."""
import json
import os
import shutil
import subprocess
import sys

import pytest

from conftest import CONFORMANCE, DEFAULT_POLICY, ROOT, require_lake

FIX = CONFORMANCE / "11-toolchain-tampering"


def audit(tmp_path, env_extra, pythonpath):
    proj = tmp_path / "proj"
    shutil.copytree(FIX, proj, ignore=shutil.ignore_patterns(".lake"))
    out = tmp_path / "report.json"
    env = {**os.environ, "PYTHONPATH": str(pythonpath), **env_extra}
    p = subprocess.run([sys.executable, "-m", "auditor", "check", str(proj / "Fixture" / "Tamper.lean"),
                        "--output", str(out), "--policy", str(DEFAULT_POLICY)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=900)
    return p.returncode, json.loads(out.read_text(encoding="utf-8"))


def reasons(report):
    return [r["code"] for d in report["declarations"] for r in d["proof_status"]["reasons"]]


def test_tampering_with_the_auditor_package_is_detected(tmp_path):
    require_lake()
    src = tmp_path / "src"
    shutil.copytree(ROOT / "src" / "auditor", src / "auditor", ignore=shutil.ignore_patterns("__pycache__"))
    target = src / "auditor" / "aggregator.py"
    code, r = audit(tmp_path, {"AUDITOR_TAMPER_TARGET": str(target)}, src)
    assert "# adulterado" in target.read_text(encoding="utf-8")       # o build executou e adulterou
    assert code == 1
    assert {d["overall_status"] for d in r["declarations"]} == {"unresolved"}
    assert set(reasons(r)) == {"toolchain_tampered"}
    detail = next(x["detail"] for d in r["declarations"] for x in d["proof_status"]["reasons"])
    assert detail == {"changed": ["auditor_package"]}


def test_tampering_with_the_inspector_binary_is_detected(tmp_path):
    require_lake()
    from auditor.tier1 import stage_b
    cache = tmp_path / "cache"
    toolchain = (FIX / "lean-toolchain").read_text(encoding="utf-8").strip()
    _, key = stage_b.inspector_identity(toolchain)
    exe = cache / "inspector" / key / ".lake" / "build" / "bin" / ("inspect.exe" if os.name == "nt" else "inspect")
    env = {"AUDITOR_TAMPER_TARGET": str(exe), "AUDITOR_CACHE": str(cache)}
    code, r = audit(tmp_path, env, ROOT / "src")
    assert exe.is_file()
    assert code == 1
    assert set(reasons(r)) == {"toolchain_tampered"}
    detail = next(x["detail"] for d in r["declarations"] for x in d["proof_status"]["reasons"])
    assert detail == {"changed": ["inspector"]}


def test_execution_without_tampering_is_rejected_not_tampered(tmp_path):
    """Sem alvo de adulteração, o hash não muda: o que vale é o (a), `run_tac` → Rejeitada."""
    require_lake()
    code, r = audit(tmp_path, {"AUDITOR_TAMPER_TARGET": ""}, ROOT / "src")
    assert code == 1
    assert "toolchain_tampered" not in reasons(r)
    assert {d["overall_status"] for d in r["declarations"]} == {"rejected"}
