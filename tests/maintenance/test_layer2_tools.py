"""Ferramentas da camada 2 (tools/layer2): escolha do arquivo de maior fanout e tempos por
cache_state. Testadas aqui para que a evidência da camada 2 venha de procedimento verificado."""
import json
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools" / "layer2"))
import fanout    # noqa: E402
import timings   # noqa: E402


def test_header_imports_stops_at_first_command_and_skips_comments():
    text = ("/-\nCopyright /- aninhado -/ fim\n-/\nmodule\n-- comentário\nimport A.B C\n"
            "public import D  -- fim de linha\n\nimport E\ntheorem t : True := trivial\nimport F\n")
    assert fanout.header_imports(text) == ["A.B", "C", "D", "E"]


def test_header_imports_rejects_illegible_names():
    with pytest.raises(fanout.HeaderError):
        fanout.header_imports("import A.«B»\n")


def test_fanout_is_transitive_and_ranked(tmp_path):
    lib = tmp_path / "L"
    (lib / "Sub").mkdir(parents=True)
    (lib / "Base.lean").write_text("import Init\n", encoding="utf-8")
    (lib / "Mid.lean").write_text("import L.Base\n", encoding="utf-8")
    (lib / "Sub" / "Top.lean").write_text("import L.Mid\nimport Mathlib.Foo\n", encoding="utf-8")
    (lib / "Other.lean").write_text("import L.Base\n", encoding="utf-8")
    (tmp_path / "L.lean").write_text("import L.Sub.Top\nimport L.Other\n", encoding="utf-8")
    rows = fanout.ranking(tmp_path, "L")
    assert [(r["module"], r["direct"], r["transitive"], r["imports_transitive"]) for r in rows] == [
        ("L.Base", 2, 4, 0), ("L.Mid", 1, 2, 1), ("L.Other", 1, 1, 1), ("L.Sub.Top", 1, 1, 2), ("L", 0, 0, 4)]
    assert rows[0]["file"] == "L/Base.lean"


def _outcome(state, elapsed, files, first_run=False, infra=False):
    return {"schema": timings.SCHEMA, "cache_state": state, "first_run": first_run, "infra_failed": infra,
            "elapsed_s": elapsed, "setup_elapsed_s": elapsed / 2, "audit_elapsed_s": elapsed / 2,
            "steady_state_budget_s": 300.0,
            "files": [{"duration_s": d, "exit_code": 0, "status": "pass"} for d in files]}


def test_timings_by_cache_state(tmp_path):
    for i, o in enumerate([_outcome("warm", 100, [10, 20]), _outcome("warm", 400, [30]),
                           _outcome("cold", 800, [60], first_run=True)]):
        d = tmp_path / f"run{i}"
        d.mkdir()
        (d / "outcome.json").write_text(json.dumps(o), encoding="utf-8")
    s = timings.summarize(timings.load([tmp_path]))
    assert s["warm"]["runs"] == 2 and s["warm"]["elapsed_median_s"] == 250
    assert s["warm"]["file_p95_s"] == 30 and s["warm"]["within_steady_state_budget"] == 1
    assert s["cold"]["first_run"] == 1 and "delta" not in s


def test_timings_rejects_foreign_outcome(tmp_path):
    p = tmp_path / "outcome.json"
    p.write_text(json.dumps({"schema": "auditor-ci-outcome/1"}), encoding="utf-8")
    with pytest.raises(timings.OutcomeError):
        timings.load([p])
    assert timings.main([str(p)]) == 2
