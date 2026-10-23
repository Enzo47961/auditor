"""Ferramentas de medição da Fase 1 (tools/phase1): causas de fail-closed da Etapa A (P0-2) e
`implemented_by` escritos × gerados (P0-1). Testadas para que a medição venha de procedimento
verificado; o teste de ponta a ponta confere que a medição concorda com o próprio auditor."""
import json
import os
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
    exe = b / ".lake" / "build" / "bin" / ("implemented_by_scan.exe" if os.name == "nt" else "implemented_by_scan")
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


# ------------------------------------------------------------------ 1b: benchmark

import benchmark as bench  # noqa: E402


def _case(i, cat, **kw):
    return {"id": i, "category": cat, "module": f"M.{i}", "declaration": f"d{i}",
            "expected": kw.pop("expected", {"verified": cat in bench.POSITIVE}), **kw}


def test_benchmark_report_counts_by_category_with_validity():
    manifest = {"cases": [
        _case("P1", "correct_hard"), _case("P2", "correct_hard"),
        _case("V1", "swap_control", controls="S1"), _case("V2", "swap_control", controls="S2"),
        _case("S1", "swapped_statement", expected={"verified": False, "reasons_any": ["compile_failure"]},
              ground_truth={"module": "G.1", "declaration": "g1"}),
        _case("S2", "swapped_statement", expected={"verified": False, "reasons_any": ["compile_failure"]},
              ground_truth={"module": "G.2", "declaration": "g2"}),          # controle falhou → inválido
        _case("C1", "sorry_axiom", expected={"verified": False, "reasons_any": ["sorryAx_detected"]},
              ground_truth={"module": "G.1", "declaration": "g1"}),
        _case("C2", "sorry_axiom", expected={"verified": False, "reasons_any": ["sorryAx_detected"]},
              ground_truth={"module": "G.9", "declaration": "g9"}),          # ground truth falhou → inválido
    ]}
    R = lambda i, ov, codes=(), gt=None: {"id": i, "found": True, "overall": ov, "codes": list(codes),  # noqa: E731
                                          **({"ground_truth": {"verified": gt}} if gt is not None else {})}
    data = {"results": [
        R("P1", "verified"), R("P2", "unresolved", ["implemented_by_candidate"]),
        R("V1", "verified"), R("V2", "unresolved", ["compile_failure"]),
        R("S1", "unresolved", ["compile_failure"], gt=True), R("S2", "unresolved", ["compile_failure"], gt=True),
        R("C1", "rejected", ["sorryAx_detected"], gt=True), R("C2", "verified", [], gt=False),
    ]}
    r = bench.report(data, manifest)
    c = r["by_category"]
    assert (c["correct_hard"]["valid"], c["correct_hard"]["false_positive_rate"]) == (2, 0.5)
    assert c["correct_hard"]["alerts_on"][0]["codes"] == ["implemented_by_candidate"]
    assert (c["swapped_statement"]["valid"], c["swapped_statement"]["sensitivity"]) == (1, 1.0)
    assert [x["id"] for x in c["swapped_statement"]["invalid"]] == ["S2"]
    assert (c["sorry_axiom"]["valid"], c["sorry_axiom"]["false_negatives"], c["sorry_axiom"]["reason_ok"]) == (1, 0, 1)
    assert r["alerts_on_negatives"] == 2 and r["alerts_on_positives"] == 2 and r["precision"] == 0.5


def test_benchmark_false_negative_is_reported():
    manifest = {"cases": [_case("C1", "sorry_axiom", expected={"verified": False, "reasons_any": ["x"]})]}
    data = {"results": [{"id": "C1", "found": True, "overall": "verified", "codes": []}]}
    r = bench.report(data, manifest)
    assert r["by_category"]["sorry_axiom"]["misses"] == ["C1"] and "FALSO NEGATIVO" in bench.to_md(r)


def test_benchmark_manifest_is_consistent():
    """Todo caso negativo tem ground truth ou controle; toda troca tem controle; ids únicos."""
    m = json.loads((ROOT / "benchmark" / "manifest.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in m["cases"]]
    assert len(ids) == len(set(ids))
    swaps = {c["id"] for c in m["cases"] if c["category"] == "swapped_statement"}
    assert swaps == {c["controls"] for c in m["cases"] if c["category"] == "swap_control"}
    for c in m["cases"]:
        if c["category"] in bench.NEGATIVE:
            assert c.get("ground_truth"), c["id"]
        assert (ROOT / "benchmark" / "lean").exists()
        if c["module"].startswith("Mathlib.AuditorBenchmark."):
            rel = c["module"][len("Mathlib.AuditorBenchmark."):].replace(".", "/") + ".lean"
            assert (ROOT / "benchmark" / "lean" / rel).is_file(), rel


# ------------------------------------------------------------------ 1c: seleção e exclusão (B)

import study_audit  # noqa: E402
import study_select  # noqa: E402


def _f(name, add=1, rem=0, status="modified"):
    return {"filename": name, "additions": add, "deletions": rem, "status": status}


@pytest.mark.parametrize("files,ok", [
    ([_f("Mathlib/Algebra/X.lean", 10)], True),
    ([_f("Mathlib/Algebra/X.lean"), _f("docs/100.yaml")], True),                  # docs/ é documentação
    ([_f("Mathlib/Algebra/X.lean"), _f(".github/workflows/ci.yml")], False),
    ([_f("Mathlib/Algebra/X.lean"), _f("docs/notes.md")], True),
    ([_f("Mathlib/Tactic/X.lean")], False),
    ([_f(f"Mathlib/A/X{i}.lean") for i in range(6)], False),
    ([_f("Mathlib/Algebra/X.lean", 200, 101)], False),
    ([_f("Mathlib/Algebra/X.lean", status="removed")], False),
    ([_f("lake-manifest.json")], False),
])
def test_study_selection_criteria(files, ok):
    assert study_select.criteria(files)[0] is ok


def test_study_exclusion_rule(tmp_path):
    def rep(name, reasons, cands=()):
        p = tmp_path / name
        p.write_text(json.dumps({"file_findings": {"stage_a_candidates": list(cands)},
                                 "declarations": [{"overall_status": "unresolved" if reasons else "verified",
                                                   "proof_status": {"reasons": reasons}}]}))
        return {"report": name}
    ctor = rep("a.json", [{"code": "implemented_by_candidate", "detail": {"constants": ["Foo.ctorIdx"]}}])
    other_ib = rep("b.json", [{"code": "implemented_by_candidate", "detail": {"constants": ["Foo.impl"]}}])
    back = rep("c.json", [{"code": "set_option_unattributed", "detail": {"line": 7}}],
               [{"code": "set_option", "line": 7, "option": "backward.isDefEq.respectTransparency"}])
    clean = rep("d.json", [])
    assert study_audit.exclusion(tmp_path, {"A": ctor})[0] == ["ctorIdx"]
    assert study_audit.exclusion(tmp_path, {"B": other_ib})[0] == []
    assert study_audit.exclusion(tmp_path, {"C": back})[0] == ["backward.*"]
    causes, counts = study_audit.exclusion(tmp_path, {"D": clean, "A": ctor})
    assert causes == ["ctorIdx"] and counts == {"declarations": 2, "verified": 1}


def test_l35_marginal_cost_split_by_kind():
    execcap = {"modules_in_root": 4, "reportable_in_root": 100, "flagged_modules": [
        {"module": "Mathlib.A", "reportable": 10, "flagged": [{"name": "A.delabFoo", "reason": "io_type"}]},
        {"module": "Mathlib.B", "reportable": 20, "flagged": [{"name": "B._aux_Mathlib_B___delab_app_x", "reason": "io_type"}]},
        {"module": "Mathlib.C", "reportable": 30, "flagged": [{"name": "C.f", "reason": "extern"}]}]}
    causes = {"files": [{"file": "Mathlib/A.lean", "clean": True}, {"file": "Mathlib/B.lean", "clean": False},
                        {"file": "Mathlib/C.lean", "clean": True}, {"file": "Mathlib/D.lean", "clean": True}]}
    r = ibm.l35(execcap, causes)
    assert r["flagged"] == {"modules": 3, "reportable": 60, "modules_pct": 75.0, "reportable_pct": 60.0}
    assert r["flagged_handwritten"]["modules"] == 1 and r["flagged_generated_only"]["modules"] == 1
    assert r["marginal"]["reportable"] == 40 and r["marginal_handwritten"]["reportable"] == 10
    assert r["marginal_generated_only"]["modules"] == 0
