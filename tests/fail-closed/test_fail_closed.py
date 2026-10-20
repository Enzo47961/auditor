"""Critério de aceitação 6: nenhum `Validada`/`verified` com input não reconhecido.

Fim a fim (CLI). Vermelho até o CLI existir."""
import pytest

from conftest import FAIL_CLOSED, run_auditor

CASES = {
    "macro-custom": "Fixture/Target.lean",
    "namespace-unicode": "Fixture/Target.lean",
    "circular-dependency": "Fixture/A.lean",
}


@pytest.mark.parametrize("fixture", sorted(CASES))
def test_never_verified(fixture, tmp_path):
    r = run_auditor(FAIL_CLOSED / fixture / CASES[fixture], tmp_path)
    assert r.exit_code != 0
    assert r.report is not None, f"fail-closed exige relatório com razão explícita: {r.stderr}"
    for d in r.report["declarations"]:
        assert d["proof_status"]["value"] != "Validada"
        assert d["overall_status"] != "verified"
