"""Ferramentas de medição da Fase 1 (tools/phase1): causas de fail-closed da Etapa A (P0-2) e
`implemented_by` escritos × gerados (P0-1). Testadas para que a medição venha de procedimento
verificado; o teste de ponta a ponta confere que a medição concorda com o próprio auditor."""
import json
import subprocess
import sys

import pytest

from conftest import CONFORMANCE, ROOT, require_lake, run_auditor

sys.path.insert(0, str(ROOT / "tools" / "phase1"))
import implemented_by_measure as ibm  # noqa: E402
import stage_a_causes  # noqa: E402

TOOLCHAIN = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()
FIX08 = CONFORMANCE / "08-generated-implemented-by"


@pytest.mark.parametrize("code,cause", [
    ("unknown_command", "false_positive"), ("metaprogramming_command", "non_syntactic"),
    ("unclassified_command", "non_syntactic"), ("syntax_extension_declared", "syntax"),
    ("declaration_name_unresolved", "other"), ("forbidden_unicode", "other"),
])
def test_cause_of(code, cause):
    assert stage_a_causes.cause_of(code) == cause


def test_stage_a_causes_counts_files_by_cause_and_only_cause(tmp_path):
    (tmp_path / "lean-toolchain").write_text(TOOLCHAIN + "\n")
    srcs = {"A.lean": "theorem a : True := trivial\n",                   # limpo
            "B.lean": "macro \"x\" : term => `(1)\n",                    # sintaxe
            "C.lean": "run_cmd pure ()\nmacro \"y\" : term => `(2)\n",   # não sintático + sintaxe
            "D.lean": "lemma d : True := trivial\n"}                    # desconhecido no core
    for f, s in srcs.items():
        (tmp_path / f).write_text(s, encoding="utf-8")
    rows = [{"file": f, "transitive": 0} for f in srcs]
    files = stage_a_causes.scan(tmp_path, rows, None)
    s = stage_a_causes.summarize(files)
    assert (s["files"], s["clean"], s["failing"]) == (4, 1, 3)
    assert s["files_by_cause"] == {"false_positive": 1, "non_syntactic": 1, "syntax": 2, "other": 0}
    assert s["files_only_cause"] == {"false_positive": 1, "non_syntactic": 0, "syntax": 1, "other": 0}
    assert s["files_by_key"]["non_syntactic"] == {"run_cmd": 1}


@pytest.mark.parametrize("name,base,last", [
    ("instImpl._@.Fixture.Target.1134090528._hygCtx._hyg.8", "instImpl", "instImpl"),
    ("Color.ctorIdx._impl", "Color.ctorIdx._impl", "_impl"),
    ("Foo", "Foo", "Foo"),
])
def test_names(name, base, last):
    assert ibm.base_name(name) == base and ibm.last(name) == last


def test_report_only_generated_and_percentages():
    cls = {"root": "R", "categories": ibm.CATEGORIES, "rows": [
        {"categories": ["generated_ctor_idx"]}, {"categories": ["source_written"]}],
        "by_category_and_package": {}, "generated_other_first_token": {}}
    masks = [{"mask": 0, "count": 90, "categories": [], "examples": []},
             {"mask": 2, "count": 6, "categories": ["generated_ctor_idx"], "examples": ["a"]},
             {"mask": 3, "count": 3, "categories": ["source_written", "generated_ctor_idx"], "examples": []},
             {"mask": 12, "count": 1, "categories": ["generated_type_name", "generated_other"], "examples": []}]
    reach = {"categories": ibm.CATEGORIES, "reportable_in_root": 100, "masks": masks, "areas": [],
             "missing_seeds": []}
    r = ibm.report(cls, reach)
    assert r["declarations_reaching_any"] == 10
    assert r["declarations_reaching_only_generated"] == 7
    assert r["declarations_reaching_only_ctor_idx"] == 6
    assert r["declarations_reaching_category"]["source_written"] == 3
    assert r["declarations_reaching_only_generated_pct"] == 7.0


def test_measurement_agrees_with_the_auditor_on_fixture_08(tmp_path):
    """P0-1 de ponta a ponta no cenário 08: o scanner + classificação marcam exatamente as
    declarações que o auditor deixa `implemented_by_candidate`."""
    lake = require_lake()
    b = tmp_path / "ibscan"
    b.mkdir()
    (b / "ImplementedByScan.lean").write_bytes((ROOT / "tools" / "phase1" / "ImplementedByScan.lean").read_bytes())
    (b / "lean-toolchain").write_text(TOOLCHAIN + "\n")
    (b / "lakefile.lean").write_text("import Lake\nopen Lake DSL\npackage ibscan\n@[default_target] lean_exe "
                                     "implemented_by_scan where\n  root := `ImplementedByScan\n"
                                     "  supportInterpreter := true\n")
    subprocess.run([lake, "build"], cwd=b, check=True, capture_output=True, timeout=900)
    exe = next((b / ".lake" / "build" / "bin").glob("implemented_by_scan*"))
    subprocess.run([lake, "build"], cwd=FIX08, check=True, capture_output=True, timeout=900)
    run = lambda *a: subprocess.run([lake, "env", str(exe), *a], cwd=FIX08, check=True,  # noqa: E731
                                    capture_output=True, timeout=900)
    run("dump", "Fixture.Target", str(tmp_path / "dump.json"))
    cls = ibm.classify(FIX08, json.loads((tmp_path / "dump.json").read_text(encoding="utf-8")))
    (tmp_path / "seeds.json").write_text(json.dumps({"categories": ibm.CATEGORIES, "seeds": cls["seeds"]}))
    run("reach", "Fixture.Target", str(tmp_path / "seeds.json"), str(tmp_path / "reach.json"))
    reach = json.loads((tmp_path / "reach.json").read_text(encoding="utf-8"))
    assert reach["missing_seeds"] == []
    flagged = sorted(e for m in reach["masks"] if m["mask"] for e in m["examples"])
    audited = run_auditor(FIX08 / "Fixture" / "Target.lean", tmp_path)
    expected = sorted(d["declaration_name"] for d in audited.report["declarations"]
                      if any(r["code"] == "implemented_by_candidate" for r in d["proof_status"]["reasons"]))
    assert flagged == expected == ["idx_red", "instTypeNameTag", "red_ne_green", "tag_name"]
    cats = {r["name"].split("._@.")[0]: r["categories"] for r in cls["rows"] if r["categories"]}
    assert cats == {"Color.ctorIdx": ["generated_ctor_idx"], "Shape.ctorIdx": ["generated_ctor_idx"],
                    "inst": ["generated_type_name"]}
