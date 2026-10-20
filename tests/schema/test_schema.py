"""Critério 4: todo relatório passa no JSON Schema v1; o schema publicado é o empacotado;
o schema rejeita relatórios que violariam os princípios (Q4, TCB completa, correspondência)."""
import copy
import json

import pytest

from auditor.schema import SCHEMA_FILE, validation_errors
from conftest import CONFORMANCE, FAIL_CLOSED, ROOT, run_auditor

TARGETS = [
    CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean",
    CONFORMANCE / "02-sorry-transitive" / "Fixture" / "A.lean",
    CONFORMANCE / "03-axiom-unknown" / "Fixture" / "Target.lean",
    CONFORMANCE / "04-implemented-by" / "Fixture" / "Target.lean",
    CONFORMANCE / "04b-extern" / "Fixture" / "Target.lean",
    CONFORMANCE / "05-native-decide" / "Fixture" / "Target.lean",
    CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean",
    FAIL_CLOSED / "macro-custom" / "Fixture" / "Target.lean",
    FAIL_CLOSED / "namespace-unicode" / "Fixture" / "Target.lean",
    FAIL_CLOSED / "circular-dependency" / "Fixture" / "A.lean",
]
_reports: dict = {}


def report(t, tmp_path_factory):
    if t not in _reports:
        r = run_auditor(t, tmp_path_factory.mktemp("s"))
        assert r.report is not None, r.stderr
        _reports[t] = r.report
    return _reports[t]


def test_published_schema_is_packaged_schema():
    assert (ROOT / "schema" / "report-v1.json").read_bytes() == SCHEMA_FILE.read_bytes()


@pytest.mark.parametrize("t", TARGETS, ids=lambda p: p.parent.parent.name)
def test_every_report_validates(t, tmp_path_factory):
    assert validation_errors(report(t, tmp_path_factory)) == []


def _verified(tmp_path_factory):
    r = report(TARGETS[6], tmp_path_factory)      # 06: tudo verified, exit 0
    assert r["exit_code"] == 0
    return copy.deepcopy(r)


@pytest.mark.parametrize("break_it", [
    lambda r: r["declarations"][0].__setitem__("overall_status", "rejected"),      # Q4 inconsistente
    lambda r: r["declarations"][0].__setitem__("correspondence_status", "Auditada"),
    lambda r: r["declarations"][0]["tcb"].__setitem__("inspector", None),          # Validada sem TCB
    lambda r: r["declarations"][0]["proof_status"]["reasons"].append({"code": "x", "detail": {}}),
    lambda r: r["declarations"][0].__setitem__("seal", "selo sem a declaração"),
    lambda r: r["file_findings"]["unrecognized"].append({"code": "unknown_command"}),  # exit 0 com input não reconhecido
    lambda r: r.__setitem__("declarations", []),                                   # exit 0 sem declarações
    lambda r: r["declarations"][0].__setitem__("justification", {"reason": "x", "reviewer": "sem-arroba"}),
])
def test_schema_rejects_principle_violations(tmp_path_factory, break_it):
    r = _verified(tmp_path_factory)
    break_it(r)
    assert validation_errors(r) != []
