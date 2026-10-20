"""Ground truth dos fixtures fail-closed, sem o auditor.

Mostra que o fail-closed é necessário: os dois primeiros compilam e o kernel aceita
sem axiomas — só a Etapa A impede `Validada`. O terceiro é rejeitado pelo próprio lake."""
import subprocess

import pytest

from conftest import FAIL_CLOSED, require_lake


@pytest.mark.parametrize("fixture,decl", [
    ("macro-custom", "two_plus_two"),
    ("namespace-unicode", "«Nat\u200bExtra».trivially"),
])
def test_compiles_without_axioms(fixture, decl):
    lake = require_lake()
    proj = FAIL_CLOSED / fixture
    assert subprocess.run([lake, "build"], cwd=proj, capture_output=True).returncode == 0
    g = subprocess.run([lake, "env", "lean", "GroundTruth.lean"], cwd=proj,
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stdout + g.stderr
    assert f"'{decl}' does not depend on any axioms" in g.stdout


def test_circular_rejected_by_lake():
    lake = require_lake()
    b = subprocess.run([lake, "build"], cwd=FAIL_CLOSED / "circular-dependency",
                       capture_output=True, text=True)
    assert b.returncode != 0
    assert "build cycle detected" in b.stdout + b.stderr
