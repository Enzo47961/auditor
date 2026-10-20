"""Testes da Etapa B (inspetor Lean + wrapper). Só fatos brutos: nenhuma política.

Ground truth: `#print axioms` (via `GroundTruth.lean` de cada fixture) e a própria
estrutura dos fixtures. Ausência de `lake` é falha explícita, nunca skip."""
import dataclasses
import hashlib
import shutil
import subprocess

import pytest

from auditor.tier1 import stage_b as B
from conftest import CONFORMANCE, FAIL_CLOSED, ROOT, parse_print_axioms, require_lake

EDGES = ROOT / "tests" / "stage_b" / "edges"
TARGETS = {
    "01": CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean",
    "02": CONFORMANCE / "02-sorry-transitive" / "Fixture" / "A.lean",
    "03": CONFORMANCE / "03-axiom-unknown" / "Fixture" / "Target.lean",
    "04": CONFORMANCE / "04-implemented-by" / "Fixture" / "Target.lean",
    "04b": CONFORMANCE / "04b-extern" / "Fixture" / "Target.lean",
    "05": CONFORMANCE / "05-native-decide" / "Fixture" / "Target.lean",
    "06": CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean",
    "edges": EDGES / "Fixture" / "Edges.lean",
    "macro": FAIL_CLOSED / "macro-custom" / "Fixture" / "Target.lean",
    "unicode": FAIL_CLOSED / "namespace-unicode" / "Fixture" / "Target.lean",
    "circular": FAIL_CLOSED / "circular-dependency" / "Fixture" / "A.lean",
}
REPORTED = {
    "01": {"foo", "ok"},
    "02": {"a_main", "a_clean"},
    "03": {"usa_axioma", "nao_usa"},
    "04": {"g", "gImpl", "g_zero", "f", "fImpl", "f_bad"},
    "04b": {"h", "h_zero", "e_zero", "e_bad", "e_mixed"},
    "06": {"add_native", "add_kernel"},
    "05": {"nd_nodoc", "nd_plain_doc", "nd_justified", "drift_holder", "drift_victim",
           "bad_multiline", "bad_escape", "bad_no_reviewer", "bad_handle", "bad_duplicate",
           "consumes_justified", "consumes_unjustified"},
    "edges": {"secret", "I", "I.mk", "uses_I", "_private.Fixture.Edges.0.hidden", "uses_hidden",
              "outer", "outer.aux", "m", "P", "P.mk", "P.x", "instInhabitedP", "loop",
              "local_ax", "uses_local"},
    "macro": {"two_plus_two", "tacticObviously"},   # `macro` gera o parser como constante
    "unicode": {"«Nat​Extra».trivially"},
}
_cache: dict = {}


def inspect(key: str) -> B.StageBResult:
    if key not in _cache:
        require_lake()
        _cache[key] = B.analyze(TARGETS[key])
    return _cache[key]


def decl(r: B.StageBResult, name: str) -> dict:
    m = [d for d in r.declarations if d["name"] == name]
    assert len(m) == 1, f"{name!r} ausente ou duplicada"
    return m[0]


def owners(d: dict, axiom: str) -> set:
    return {x["owner"] for ref in d["axiom_referrers"] if ref["axiom"] == axiom for x in ref["referrers"]}


def externs(d: dict, level: str) -> set:
    return {e["name"] for e in d["extern"] if e["level"] == level}


# ------------------------------------------------------------------ contrato

def test_result_has_no_positive_conclusion_field():
    fields = {f.name for f in dataclasses.fields(B.StageBResult)}
    assert fields == {"file", "project_root", "module", "toolchain", "stage_b_version", "build",
                      "inspector", "declarations", "anomalies", "unrecognized", "owners",
                      "boundary", "metadata"}


def test_inspector_version_matches_source():
    assert f'def inspectorVersion : String := "{B.INSPECTOR_VERSION}"' in \
        B.INSPECT_SRC.read_text(encoding="utf-8")


# ------------------------------------------------------------------ todos os fixtures

@pytest.mark.parametrize("key", sorted(REPORTED))
def test_reported_declarations_exact(key):
    r = inspect(key)
    assert r.build["status"] == "success" and r.unrecognized == [], (r.build, r.unrecognized)
    assert {d["name"] for d in r.declarations} == REPORTED[key]


@pytest.mark.parametrize("key", sorted(REPORTED))
def test_closure_agrees_with_official_and_nothing_missing(key):
    r = inspect(key)
    assert r.anomalies == []
    for d in r.declarations:
        assert d["axioms_official"] == d["axioms_closure"], d["name"]
        assert d["missing"] == []


@pytest.mark.parametrize("key", sorted(REPORTED))
def test_tcb_identity_present(key):
    r = inspect(key)
    assert r.inspector["source_sha256"] == "sha256:" + hashlib.sha256(
        B.INSPECT_SRC.read_bytes()).hexdigest()
    assert r.inspector["binary_sha256"].startswith("sha256:")
    assert r.inspector["lean_version"] == B.expected_lean_version(r.toolchain)
    assert set(r.metadata) == {"simp", "ext", "reducible", "implemented_by"}
    assert all(v["count"] > 0 for v in r.metadata.values())   # o core tem de todos


# ------------------------------------------------------------------ cenários

def test_01_sorry_owner_is_target_declaration():
    r = inspect("01")
    assert decl(r, "foo")["axioms_official"] == ["sorryAx"]
    assert owners(decl(r, "foo"), "sorryAx") == {"foo"}
    assert decl(r, "ok")["axioms_official"] == []


def test_02_transitive_sorry_traced_to_d():
    a = decl(inspect("02"), "a_main")
    assert a["axioms_official"] == ["sorryAx"]
    assert owners(a, "sorryAx") == {"d_lemma"}


def test_03_unknown_axiom_is_a_fact_not_a_judgement():
    d = decl(inspect("03"), "usa_axioma")
    assert d["axioms_official"] == ["minhaAxioma"]
    assert owners(d, "minhaAxioma") == {"usa_axioma"}


def test_04_implemented_by_facts():
    r = inspect("04")
    ib = lambda n: {(i["name"], i["implementation"], i["level"]) for i in decl(r, n)["implemented_by"]}
    assert ib("g") == ib("g_zero") == {("g", "gImpl", "user")}
    assert ib("f") == ib("f_bad") == {("f", "fImpl", "user")}
    assert ib("gImpl") == ib("fImpl") == set()
    assert decl(r, "f_bad")["axioms_official"] == ["Lean.ofReduceBool"]
    assert owners(decl(r, "f_bad"), "Lean.ofReduceBool") == {"f_bad"}
    assert decl(r, "g_zero")["axioms_official"] == []


def test_04b_extern_facts():
    r = inspect("04b")
    assert externs(decl(r, "e_bad"), "user") == {"myF"}
    assert externs(decl(r, "e_zero"), "user") == {"myF"}
    assert externs(decl(r, "h"), "user") == externs(decl(r, "h_zero"), "user") == {"h"}
    assert owners(decl(r, "e_bad"), "Lean.ofReduceBool") == {"e_bad"}
    myf = [e for e in decl(r, "e_bad")["extern"] if e["name"] == "myF"][0]
    assert myf["module"] == "Fixture.Dep"


def test_04b_case_c_only_user_extern_is_user_level():
    """(c): `myF` (usuário) e `Nat.add` (toolchain) no mesmo enunciado: só `myF` é user-level."""
    d = decl(inspect("04b"), "e_mixed")
    assert externs(d, "user") == {"myF"}
    assert "Nat.add" in externs(d, "tcb")
    assert externs(d, "unresolved") == set()


def test_06_tcb_boundary_canary():
    """Canário da fronteira (Q7): `Nat.add` é `@[extern]` de `Init.Prelude`, declarado pelo
    toolchain, e nada no fecho é user-level. Se o Lean mover `Nat.add` ou a fronteira mudar,
    este teste falha e a política precisa ser revista (docs/tcb.md)."""
    r = inspect("06")
    assert r.boundary["toolchain_roots"] == ["Init", "Lake", "LakeMain", "Lean", "Leanc", "Std"]
    for n in ("add_native", "add_kernel"):
        d = decl(r, n)
        nat_add = [e for e in d["extern"] if e["name"] == "Nat.add"]
        assert nat_add and nat_add[0]["module"] == "Init.Prelude", n
        assert nat_add[0]["level"] == "tcb" and nat_add[0]["level_reason"] == "toolchain_root"
        assert externs(d, "user") == externs(d, "unresolved") == set()
        assert all(i["level"] == "tcb" for i in d["implemented_by"])


def test_every_attribute_entry_is_classified():
    for key in sorted(REPORTED):
        for d in inspect(key).declarations:
            for e in d["implemented_by"] + d["extern"]:
                assert e["level"] in ("tcb", "user"), (key, d["name"], e)


def test_owner_docstrings_include_owners_outside_target():
    r = inspect("02")
    assert "d_lemma" in r.owners and r.owners["d_lemma"]["module"] == "Fixture.D"
    r5 = inspect("05")
    assert r5.owners["nd_justified"]["docstring"].splitlines()[1].rstrip() ==         'auditor_justified: reason="kernel decide too slow" reviewer="@enzo"'


def test_05_owner_attribution():
    r = inspect("05")
    for n in REPORTED["05"] - {"drift_holder", "consumes_justified", "consumes_unjustified"}:
        assert owners(decl(r, n), "Lean.ofReduceBool") == {n}, n
    assert owners(decl(r, "consumes_justified"), "Lean.ofReduceBool") == {"nd_justified"}
    assert owners(decl(r, "consumes_unjustified"), "Lean.ofReduceBool") == {"nd_nodoc"}
    assert decl(r, "drift_holder")["axioms_official"] == []
    assert decl(r, "consumes_unjustified")["depends_on"] == ["nd_nodoc"]


def test_05_docstrings_read_from_olean():
    r = inspect("05")
    assert decl(r, "nd_nodoc")["docstring"] is None
    assert decl(r, "nd_justified")["docstring"].splitlines()[1].rstrip() == \
        'auditor_justified: reason="kernel decide too slow" reviewer="@enzo"'


# ------------------------------------------------------------------ arestas

def test_edges_axiom_reached_only_through_constructor_type():
    d = decl(inspect("edges"), "uses_I")
    assert d["axioms_official"] == ["secret"]
    refs = {x["name"] for ref in d["axiom_referrers"] for x in ref["referrers"]}
    assert "I.mk" in refs


def test_edges_private_declaration_reported_and_owned():
    r = inspect("edges")
    assert owners(decl(r, "uses_hidden"), "sorryAx") == {"_private.Fixture.Edges.0.hidden"}


def test_edges_where_auxiliary_owned_by_top_level_declaration():
    """Convenção observada (L-4): o `native_decide` de `outer.aux` gera `outer._proof_N`,
    então a dona é `outer`. Justificativa em `outer.aux` não é encontrada → violação
    (direção segura). Se a convenção mudar, este teste acusa."""
    r = inspect("edges")
    assert owners(decl(r, "outer.aux"), "Lean.ofReduceBool") == {"outer"}
    assert owners(decl(r, "outer"), "Lean.ofReduceBool") == {"outer"}


def test_edges_internal_names_never_reported():
    for d in inspect("edges").declarations:
        tail = d["name"].split(".")[-1]
        assert not tail.startswith(("match_", "proof_", "_", "eq_")), d["name"]
        assert tail not in ("rec", "casesOn", "noConfusion", "recOn", "brecOn", "below")


def test_edges_axiom_declared_in_target():
    r = inspect("edges")
    assert decl(r, "local_ax")["kind"] == "axiom"
    assert decl(r, "local_ax")["axioms_official"] == ["local_ax"]
    assert decl(r, "uses_local")["axioms_official"] == ["local_ax"]


def test_edges_match_ground_truth():
    lake = require_lake()
    g = subprocess.run([lake, "env", "lean", "GroundTruth.lean"], cwd=EDGES, capture_output=True,
                       text=True, encoding="utf-8")
    assert g.returncode == 0, g.stdout + g.stderr
    truth = parse_print_axioms(g.stdout)
    r = inspect("edges")
    for d in r.declarations:
        if d["name"].startswith("_private."):
            continue
        assert set(d["axioms_official"]) == truth[d["name"]], d["name"]


def test_fail_closed_unicode_name_preserved():
    assert {d["name"] for d in inspect("unicode").declarations} == {"«Nat​Extra».trivially"}


def test_macro_custom_invisible_to_stage_b():
    """Sem a Etapa A, `two_plus_two` pareceria limpo: a Etapa B não vê a macro."""
    assert decl(inspect("macro"), "two_plus_two")["axioms_official"] == []


# ------------------------------------------------------------------ falhas e fail-closed

def test_circular_dependency_is_build_failure():
    r = inspect("circular")
    assert r.build["status"] == "failure" and r.build["cycle_detected"] is True
    assert r.declarations == [] and r.inspector is None


@pytest.fixture
def scratch(tmp_path):
    p = tmp_path / "proj"
    shutil.copytree(CONFORMANCE / "01-sorry-target", p, ignore=shutil.ignore_patterns(".lake"))
    return p


def test_compile_error_is_build_failure_without_cycle(scratch):
    require_lake()
    (scratch / "Fixture" / "Target.lean").write_text("theorem t : 1 = 2 := rfl\n", encoding="utf-8")
    r = B.analyze(scratch / "Fixture" / "Target.lean")
    assert r.build["status"] == "failure" and r.build["cycle_detected"] is False
    assert r.declarations == []


def test_timeout_is_not_success(scratch):
    require_lake()
    r = B.analyze(scratch / "Fixture" / "Target.lean", timeout_s=0.01)
    assert r.build["status"] == "timeout" and r.declarations == []


def test_unpinned_environment(tmp_path):
    f = tmp_path / "T.lean"
    f.write_text("theorem t : True := trivial\n", encoding="utf-8")
    r = B.analyze(f)
    assert [u["code"] for u in r.unrecognized] == ["environment_unpinned"]


def test_missing_manifest_is_unpinned(scratch):
    (scratch / "lake-manifest.json").unlink()
    r = B.analyze(scratch / "Fixture" / "Target.lean")
    assert [u["code"] for u in r.unrecognized] == ["environment_unpinned"]


def test_unresolvable_module_path(scratch):
    f = scratch / "Fixture" / "My File.lean"
    f.write_text("theorem t : True := trivial\n", encoding="utf-8")
    r = B.analyze(f)
    assert [u["code"] for u in r.unrecognized] == ["module_unresolved"]


def test_unrecognized_toolchain_format(scratch):
    (scratch / "lean-toolchain").write_text("leanprover/lean4:nightly-2099-01-01\n", encoding="utf-8")
    r = B.analyze(scratch / "Fixture" / "Target.lean")
    assert [u["code"] for u in r.unrecognized] == ["toolchain_unrecognized"]


# ------------------------------------------------------------------ ingestão (sem Lean)

def _facts(**over):
    d = {"name": "x", "kind": "theorem", "axioms_official": [], "axioms_closure": [],
         "axiom_referrers": [], "implemented_by": [], "extern": [], "missing": [],
         "depends_on": [], "docstring": None}
    f = {"inspector_version": B.INSPECTOR_VERSION, "lean_version": "4.22.0", "lean_githash": "x",
         "module": "M", "declarations": [d],
         "metadata": {k: [] for k in ("simp", "ext", "reducible", "implemented_by")}}
    for k, v in over.items():
        (d if k in d else f)[k] = v
    return f


def _ingest(facts):
    r = B.StageBResult(file="M.lean", module="M")
    B._ingest(r, facts, "4.22.0")
    return r


def test_ingest_clean():
    r = _ingest(_facts())
    assert r.unrecognized == [] and r.anomalies == []


@pytest.mark.parametrize("over,code", [
    ({"axioms_official": ["sorryAx"], "axioms_closure": []}, "inspector_disagreement"),
    ({"missing": ["Ghost"]}, "missing_constants"),
    ({"axiom_referrers": [{"axiom": "sorryAx", "referrers": [{"name": "_x", "owner": None}]}]},
     "owner_unresolved"),
])
def test_ingest_anomalies_exposed(over, code):
    assert [a["code"] for a in _ingest(_facts(**over)).anomalies] == [code]


@pytest.mark.parametrize("over,code", [
    ({"lean_version": "4.21.0"}, "toolchain_mismatch"),
    ({"inspector_version": "0"}, "inspector_version_mismatch"),
    ({"module": "Other"}, "module_mismatch"),
    ({"metadata": {"simp": []}}, "metadata_missing"),
])
def test_ingest_file_level_mismatch(over, code):
    assert code in [u["code"] for u in _ingest(_facts(**over)).unrecognized]


def test_inspector_identity_depends_on_toolchain():
    assert B.inspector_identity("leanprover/lean4:v4.22.0")[1] != \
        B.inspector_identity("leanprover/lean4:v4.21.0")[1]
