"""Ground truth independente do auditor (princípio 5).

Estes testes NÃO usam o auditor. Verificam os próprios fixtures com o Lean:
`#print axioms` como referência e, para enunciados falsos, a prova da negação
compilando. Devem estar verdes desde já; se ficarem vermelhos, o problema está
no fixture, não no auditor.
"""
import re
import subprocess

import pytest

from conftest import CONFORMANCE, ROOT, require_lake

EXPECTED_AXIOMS = {
    "01-sorry-target": {"foo": {"sorryAx"}, "ok": set()},
    "02-sorry-transitive": {"a_main": {"sorryAx"}, "a_clean": set()},
    "03-axiom-unknown": {"usa_axioma": {"minhaAxioma"}, "nao_usa": set()},
    "04-implemented-by": {"f_bad": {"Lean.ofReduceBool"}, "f_bad_is_false": set(), "g_zero": set()},
    "05-native-decide": {
        **{n: {"Lean.ofReduceBool"} for n in (
            "nd_nodoc", "nd_plain_doc", "nd_justified", "drift_victim", "bad_multiline",
            "bad_escape", "bad_no_reviewer", "bad_handle", "bad_duplicate",
            "consumes_justified", "consumes_unjustified")},
        "drift_holder": set(),
    },
}

LINE = re.compile(r"^'(?P<n>[^']+)' (?:depends on axioms: \[(?P<ax>[^\]]*)\]|does not depend on any axioms)$")


def parse_print_axioms(out: str) -> dict[str, set[str]]:
    res = {}
    for line in out.splitlines():
        m = LINE.match(line.strip())
        if m:
            ax = m.group("ax")
            res[m.group("n")] = {a.strip() for a in ax.split(",")} if ax else set()
    return res


@pytest.mark.parametrize("scenario", sorted(EXPECTED_AXIOMS))
def test_fixture_ground_truth(scenario):
    lake = require_lake()
    proj = CONFORMANCE / scenario
    b = subprocess.run([lake, "build"], cwd=proj, capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert b.returncode == 0, b.stdout + b.stderr
    g = subprocess.run([lake, "env", "lean", "GroundTruth.lean"], cwd=proj,
                       capture_output=True, text=True, encoding="utf-8", timeout=600)
    # exit 0 também prova que as negações dos enunciados falsos compilaram
    assert g.returncode == 0, g.stdout + g.stderr
    assert parse_print_axioms(g.stdout) == EXPECTED_AXIOMS[scenario]


@pytest.mark.parametrize("scenario", sorted(EXPECTED_AXIOMS))
def test_fixture_toolchain_matches_root(scenario):
    """Cópias de lean-toolchain não podem divergir da raiz (fonte única de verdade)."""
    root = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()
    assert (CONFORMANCE / scenario / "lean-toolchain").read_text(encoding="utf-8").strip() == root
