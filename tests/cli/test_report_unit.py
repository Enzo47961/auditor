"""Montagem do relatório e exit code, com resultados sintéticos das Etapas A e B (sem Lean).

Cobre caminhos difíceis de produzir com um projeto real: declaração vista só pela Etapa A
(D-14), arquivo sem declarações (D-15) e completude da TCB."""
import time

import pytest

from auditor import report as rp
from auditor.fingerprint import REQUIRED, is_complete
from auditor.policy import load_policy
from auditor.schema import validation_errors
from auditor.tier1.stage_a import Item, StageAResult
from auditor.tier1.stage_b import StageBResult
from conftest import DEFAULT_POLICY

POL = load_policy(DEFAULT_POLICY)


def decl_fact(name):
    return {"name": name, "kind": "theorem", "docstring": None, "axioms_official": [],
            "axioms_closure": [], "axiom_referrers": [], "implemented_by": [], "extern": [],
            "missing": [], "depends_on": [], "type_hash": "1", "value_hash": "2"}


def sa_with(*names):
    sa = StageAResult(file="T.lean", toolchain="leanprover/lean4:v4.22.0", allowlist={"kind": "core"})
    for i, n in enumerate(names, 1):
        sa.declarations.append(Item("declaration", i, 0, {"keyword": "theorem", "name": n}))
    return sa


def sb_with(*names):
    sb = StageBResult(file="T.lean", module="T", toolchain="leanprover/lean4:v4.22.0")
    sb.build = {"status": "success", "duration_s": 0.1}
    sb.declarations = [decl_fact(n) for n in names]
    return sb


def build(sa, sb):
    return rp.build("T.lean", sa, sb, POL, None, started=time.monotonic(), timeout_s=300, timeout_test=None)


def test_declaration_seen_only_by_stage_a_is_never_positive():
    report, code = build(sa_with("a", "ghost"), sb_with("a"))
    ghost = [d for d in report["declarations"] if d["declaration_name"] == "ghost"]
    assert ghost and ghost[0]["overall_status"] == "unresolved"
    assert ghost[0]["proof_status"]["reasons"][0]["code"] == "declaration_not_found_in_environment"
    assert "declaration_not_found_in_environment" in [u["code"] for u in report["file_findings"]["unrecognized"]]
    assert code == 1


def test_file_without_declarations_exits_1():
    report, code = build(sa_with(), sb_with())
    assert report["declarations"] == []
    assert [u["code"] for u in report["file_findings"]["unrecognized"]] == ["no_declarations"]
    assert code == 1
    assert validation_errors(report) == []


def test_file_level_unrecognized_alone_blocks_exit_0():
    """Mesmo sem declaração não `verified`, entrada não reconhecida no arquivo impede exit 0."""
    sa = sa_with()
    sa.unrecognized.append(Item("unknown_command", 1, 0, {"token": "lemma"}))
    report, code = build(sa, sb_with())
    assert code == 1


@pytest.mark.parametrize("comp", sorted(REQUIRED))
def test_tcb_missing_any_required_key_is_incomplete(comp):
    tcb = {c: {k: "x" for k in keys} for c, keys in REQUIRED.items()}
    tcb["fingerprint"] = "sha256:" + "0" * 64
    assert is_complete(tcb)
    tcb[comp] = {k: "x" for k in REQUIRED[comp][1:]}       # tira a primeira chave obrigatória
    assert not is_complete(tcb)
    tcb[comp] = None
    assert not is_complete(tcb)


def test_tcb_without_fingerprint_is_incomplete():
    tcb = {c: {k: "x" for k in keys} for c, keys in REQUIRED.items()}
    tcb["fingerprint"] = None
    assert not is_complete(tcb)
