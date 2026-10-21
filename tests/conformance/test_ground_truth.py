"""Ground truth independente do auditor (princípio 5).

Estes testes NÃO usam o auditor. Verificam os próprios fixtures com o Lean:
`#print axioms` como referência e, para enunciados falsos, a prova da negação
compilando. Devem estar verdes desde já; se ficarem vermelhos, o problema está
no fixture, não no auditor.
"""
import subprocess

import pytest

from conftest import CONFORMANCE, ROOT, parse_print_axioms, require_lake

def nax(owner):
    """v4.36: `native_decide` adiciona, por uso, o axioma `<dona>._native.native_decide.ax_1_1`
    (`Lean.Meta.nativeEqTrue`); na v4.22 era `Lean.ofReduceBool`."""
    return f"{owner}._native.native_decide.ax_1_1"


EXPECTED_AXIOMS = {
    "01-sorry-target": {"foo": {"sorryAx"}, "ok": set()},
    "02-sorry-transitive": {"a_main": {"sorryAx"}, "a_clean": set()},
    "03-axiom-unknown": {"usa_axioma": {"minhaAxioma"}, "nao_usa": set()},
    "04-implemented-by": {"f_bad": {nax("f_bad")}, "f_bad_is_false": set(), "g_zero": set()},
    "04b-extern": {"e_bad": {nax("e_bad")}, "e_bad_is_false": set(), "e_zero": set(),
                   "h_zero": set(), "e_mixed": {nax("e_mixed")}, "e_mixed_is_false": set()},
    "06-tcb-boundary": {"add_native": {nax("add_native")}, "add_kernel": set(),
                        "add_native_kernel": set(), "uses_init": set(), "uses_lean": set(),
                        "uses_std": set(), "uses_lake": {"Classical.choice"}},
    "05-native-decide": {
        **{n: {nax(n)} for n in (
            "nd_nodoc", "nd_plain_doc", "nd_justified", "drift_victim", "bad_multiline",
            "bad_escape", "bad_no_reviewer", "bad_handle", "bad_duplicate")},
        "consumes_justified": {nax("nd_justified")}, "consumes_unjustified": {nax("nd_nodoc")},
        "drift_holder": set(),
    },
}

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
