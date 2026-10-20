"""Infraestrutura comum dos testes.

Ausência de `lake` é falha explícita (environment-blocked), nunca skip:
um teste pulado não é evidência.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "tests" / "conformance"
FAIL_CLOSED = ROOT / "tests" / "fail-closed"
DEFAULT_POLICY = ROOT / "policy.toml"
CORRESPONDENCE = "Não auditada"


def require_lake() -> str:
    lake = shutil.which("lake")
    if lake is None:
        pytest.fail("environment-blocked: `lake` não encontrado no PATH")
    return lake


@dataclass
class AuditResult:
    exit_code: int
    report: dict | None
    stderr: str

    def decl(self, name: str) -> dict:
        assert self.report is not None, f"sem relatório (exit={self.exit_code}): {self.stderr}"
        matches = [d for d in self.report["declarations"] if d["declaration_name"] == name]
        assert len(matches) == 1, f"declaração {name!r} ausente ou duplicada no relatório"
        return matches[0]


def run_auditor(target: Path, tmp_path: Path, policy: Path = DEFAULT_POLICY) -> AuditResult:
    out = tmp_path / "report.json"
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "auditor", "check", str(target),
         "--output", str(out), "--policy", str(policy)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=600,
    )
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return AuditResult(proc.returncode, report, proc.stderr)


def reasons(decl: dict, key: str) -> set[str]:
    """Códigos de razão de um estado (`proof_status` ou `premises_status`)."""
    return {r["code"] for r in decl[key]["reasons"]}


def violation_rules(decl: dict) -> set[str]:
    return {v["rule"] for v in decl["policy_violations"]}


def assert_common_invariants(result: AuditResult) -> None:
    """Invariantes que valem para TODO relatório, em todo cenário."""
    assert result.report is not None, f"sem relatório: {result.stderr}"
    for d in result.report["declarations"]:
        assert d["correspondence_status"] == CORRESPONDENCE
        positive = (d["proof_status"]["value"] == "Validada"
                    and d["premises_status"]["value"] == "Conforme")
        assert (d["overall_status"] == "verified") == positive, \
            f"{d['declaration_name']}: overall_status inconsistente com os estados individuais"
        if d["proof_status"]["value"] == "Validada":
            tcb = result.report["tcb"]
            for k in ("kernel", "toolchain", "dependencies", "inspector",
                      "aggregator", "stage_a_parser", "policy", "fingerprint"):
                assert tcb.get(k), f"Validada com TCB incompleta: falta {k}"


def state(decl: dict) -> tuple[str, str, str]:
    """(proof_status, premises_status, overall_status) de uma declaração."""
    return (decl["proof_status"]["value"], decl["premises_status"]["value"], decl["overall_status"])


PRINT_AXIOMS_LINE = re.compile(
    r"^'(?P<n>[^']+)' (?:depends on axioms: \[(?P<ax>[^\]]*)\]|does not depend on any axioms)$")


def parse_print_axioms(out: str) -> dict[str, set[str]]:
    """Saída de `#print axioms` → {declaração: axiomas}. Ground truth independente do auditor."""
    res = {}
    for line in out.splitlines():
        m = PRINT_AXIOMS_LINE.match(line.strip())
        if m:
            ax = m.group("ax")
            res[m.group("n")] = {a.strip() for a in ax.split(",")} if ax else set()
    return res
