"""Ferramentas da camada 2 (tools/layer2): escolha do arquivo de maior fanout e tempos por
cache_state. Testadas aqui para que a evidência da camada 2 venha de procedimento verificado."""
import json
import sys

import pytest

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools" / "layer2"))
import fanout    # noqa: E402
import native_usage  # noqa: E402
import timings   # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import gen_tcb_roots  # noqa: E402


def test_header_imports_stops_at_first_command_and_skips_comments():
    text = ("/-\nCopyright /- aninhado -/ fim\n-/\nmodule\n-- comentário\nimport A.B C\n"
            "public import D  -- fim de linha\n\nimport E\ntheorem t : True := trivial\nimport F\n")
    assert fanout.header_imports(text) == ["A.B", "C", "D", "E"]


def test_header_imports_import_all_is_a_modifier():
    text = "module\npublic import all A.B\nimport all C\nmeta import D\n"
    assert fanout.header_imports(text) == ["A.B", "C", "D"]


def _git_repo(path):
    import subprocess
    run = lambda *a: subprocess.run(["git", "-C", str(path), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    run("add", "-A")
    run("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
    return subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True).stdout.strip()


def test_fanout_records_provenance_and_checks_commit(tmp_path, capsys):
    (tmp_path / "L").mkdir()
    (tmp_path / "L" / "A.lean").write_text("import Init\n", encoding="utf-8")
    (tmp_path / "lake-manifest.json").write_text('{"version": "1.1.0", "packages": []}', encoding="utf-8")
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:vX\n", encoding="utf-8")
    sha = _git_repo(tmp_path)
    out = tmp_path / "f.json"
    assert fanout.main([str(tmp_path), "--root", "L", "--json", str(out), "--expect-commit", sha]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["provenance"]["commit"] == sha
    assert data["provenance"]["lean_toolchain"] == "leanprover/lean4:vX"
    assert len(data["provenance"]["lake_manifest_sha256"]) == 64
    assert [r["module"] for r in data["rows"]] == ["L.A"]
    out.unlink()
    assert fanout.main([str(tmp_path), "--root", "L", "--json", str(out), "--expect-commit", "0" * 40]) == 2
    assert not out.exists()                 # commit errado: nenhum ranking


def test_native_usage_uses_stage_a_rule_and_attributes_to_declarations():
    src = ("/-- native_decide no docstring não conta -/\n"
           "theorem a : 1 = 1 := by native_decide\n"
           "-- native_decide em comentário não conta\n"
           "@[simp] private theorem b : True := by decide +native\n"
           "theorem c : True := by\n  first | bv_decide | decide (config := { native := true })\n"
           "def s : String := \"native_decide\"\n"
           "lemma d : 2 = 2 := rfl\n"
           "structure S where\n  native : Bool\n")
    r = native_usage.scan_file(src)
    assert r["declarations"] == 5                       # a, b, c, s, d (structure não tem corpo)
    assert r["native_declarations"] == 3                # a, b, c
    assert r["occurrences"] == 4
    assert r["forms"] == {"native_decide": 1, "+native": 1, "bv_decide": 1, "native := …": 1}


def test_native_usage_measure_by_area(tmp_path):
    (tmp_path / "L" / "X").mkdir(parents=True)
    (tmp_path / "L" / "X" / "A.lean").write_text("theorem a : 1 = 1 := by native_decide\ntheorem b : True := trivial\n",
                                                 encoding="utf-8")
    (tmp_path / "L" / "B.lean").write_text("theorem c : True := trivial\n", encoding="utf-8")
    m = native_usage.measure(tmp_path, "L")
    assert m["total"] == {"files": 2, "declarations": 3, "native_declarations": 1, "occurrences": 1,
                          "proportion": 1 / 3}
    assert m["areas"]["L/X"]["native_declarations"] == 1 and m["areas"]["L"]["declarations"] == 1
    assert [f["file"] for f in m["native_files"]] == ["L/X/A.lean"]


def _tcb_env(tmp_path):
    """Toolchain com raízes Init, Lean, Std, LeanIR; projeto P usa Lean (via pacote dep) e Init."""
    sysroot = tmp_path / "tc"
    lib, src = sysroot / "lib" / "lean", sysroot / "src" / "lean"
    lib.mkdir(parents=True)
    for r in ("Init", "Lean", "Std", "LeanIR"):
        (lib / f"{r}.olean").write_bytes(b"")
    (src / "Init").mkdir(parents=True)
    (src / "Lean").mkdir()
    (src / "Init.lean").write_text("prelude\nimport Init.Core\n", encoding="utf-8")
    (src / "Init" / "Core.lean").write_text("prelude\n", encoding="utf-8")
    (src / "Lean.lean").write_text("import Lean.Expr\n", encoding="utf-8")
    (src / "Lean" / "Expr.lean").write_text("module\npublic import all Init.Core\n", encoding="utf-8")
    (src / "Std.lean").write_text("import Init\n", encoding="utf-8")
    (src / "LeanIR.lean").write_text("import Lean\n", encoding="utf-8")
    dep = tmp_path / "P" / ".lake" / "packages" / "dep"
    (dep / "Dep").mkdir(parents=True)
    (dep / "Dep" / "A.lean").write_text("/- comentário /- aninhado -/ -/\nimport Lean.Expr\n", encoding="utf-8")
    rev = _git_repo(dep)
    proj = tmp_path / "P"
    (proj / "P").mkdir()
    (proj / "P" / "M.lean").write_text("import Dep.A\ntheorem t : True := trivial\n", encoding="utf-8")
    (proj / "lean-toolchain").write_text("leanprover/lean4:vT\n", encoding="utf-8")
    manifest = {"version": "1.1.0", "packagesDir": ".lake/packages",
                "packages": [{"type": "git", "name": "dep", "rev": rev, "url": "x"}]}
    (proj / "lake-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return sysroot, proj, manifest


def test_gen_tcb_roots_closure_and_provenance(tmp_path):
    sysroot, proj, _ = _tcb_env(tmp_path)
    d = gen_tcb_roots.generate(sysroot, proj, "P")
    assert d["roots"] == ["Init", "Lean"]               # Std e LeanIR: declaradas, não usadas
    assert d["declared_by_toolchain"] == ["Init", "Lean", "LeanIR", "Std"]
    assert d["modules_in_closure"] == {"Init": 2, "Lean": 1}
    assert d["toolchain"] == "leanprover/lean4:vT"
    assert d["derived_from"]["packages"] == {"dep": json.loads((proj / "lake-manifest.json").read_text())
                                             ["packages"][0]["rev"]}
    out = tmp_path / "roots.json"
    args = ["--sysroot", str(sysroot), "--project", str(proj), "--root", "P", "--out", str(out)]
    assert gen_tcb_roots.main(args) == 0
    assert gen_tcb_roots.main([*args, "--check"]) == 0
    out.write_text(out.read_text(encoding="utf-8").replace('"Lean"\n', '"Lean",\n    "LeanIR"\n', 1),
                   encoding="utf-8")
    assert gen_tcb_roots.main([*args, "--check"]) == 1


def test_gen_tcb_roots_rejects_package_off_manifest_rev(tmp_path):
    sysroot, proj, manifest = _tcb_env(tmp_path)
    manifest["packages"][0]["rev"] = "0" * 40
    (proj / "lake-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(gen_tcb_roots.GenError, match="manifest fixa"):
        gen_tcb_roots.generate(sysroot, proj, "P")


def test_gen_tcb_roots_rejects_incomplete_closure(tmp_path):
    sysroot, proj, _ = _tcb_env(tmp_path)
    (proj / "P" / "N.lean").write_text("import Nowhere.X\n", encoding="utf-8")
    with pytest.raises(gen_tcb_roots.GenError, match="sem fonte"):
        gen_tcb_roots.generate(sysroot, proj, "P")


def test_versioned_tcb_roots_match_mathlib_measurement():
    """O arquivo versionado é o fecho do Mathlib fixado (gerado por gen_tcb_roots.py, D-42)."""
    data = json.loads((ROOT / "src" / "auditor" / "data" / "target_trusted_roots" /
                       "leanprover__lean4__v4.36.0-rc1.json").read_text(encoding="utf-8"))
    assert data["roots"] == ["Init", "Lake", "Lean", "Std"]
    assert data["derived_from"]["commit"] == "e1b2403bdd31a2756e30282d62b3fa54cc95c869"
    # hash do manifesto com fim de linha LF, como no repositório (D-53; o CRLF era c9b51d72…)
    assert data["derived_from"]["lake_manifest_sha256"] == \
        "f77f47dbdf33a5ca838db1937b5d128515b5c23dab39094def3975868efbbdd6"
    assert set(data["roots"]) <= set(data["declared_by_toolchain"])


def test_gen_tcb_roots_manifest_hash_ignores_crlf(tmp_path):
    import hashlib
    sysroot, proj, _ = _tcb_env(tmp_path)
    m = proj / "lake-manifest.json"
    lf = m.read_bytes().replace(b"\r\n", b"\n") + b"\n"
    m.write_bytes(lf)
    h_lf = gen_tcb_roots.generate(sysroot, proj, "P")["derived_from"]["lake_manifest_sha256"]
    m.write_bytes(lf.replace(b"\n", b"\r\n"))
    h_crlf = gen_tcb_roots.generate(sysroot, proj, "P")["derived_from"]["lake_manifest_sha256"]
    assert h_lf == h_crlf == hashlib.sha256(lf).hexdigest()
    assert fanout.provenance(proj)["lake_manifest_sha256"] == h_lf


def _fork_env(tmp_path):
    """Projeto P num repositório git; o arquivo de raízes é gravado no commit fixado."""
    import subprocess
    sysroot, proj, _ = _tcb_env(tmp_path)
    (proj / ".gitignore").write_text(".lake/\n", encoding="utf-8")
    pinned = _git_repo(proj)
    out = tmp_path / "roots.json"
    args = ["--sysroot", str(sysroot), "--project", str(proj), "--root", "P", "--out", str(out)]
    assert gen_tcb_roots.main(args) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["derived_from"]["commit"] == pinned

    def commit(rel, text):
        f = proj / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")
        for a in (["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "y"]):
            subprocess.run(["git", "-C", str(proj), *a], check=True, capture_output=True)
    return proj, args, out, commit


def test_check_accepts_fork_that_only_changes_github(tmp_path, capsys):
    """D-54: o fork de medição remove/adiciona workflows; o fecho é o mesmo do commit fixado."""
    proj, args, out, commit = _fork_env(tmp_path)
    commit(".github/workflows/auditor.yml", "on: push\n")
    assert gen_tcb_roots.main([*args, "--check"]) == 0
    assert "D-54" in capsys.readouterr().out


def test_check_accepts_fork_with_auditor_config(tmp_path, capsys):
    """D-59: o passo 3 commita `.auditor/` (classificação e allow-list) no fork; não entra no fecho."""
    proj, args, out, commit = _fork_env(tmp_path)
    commit(".github/workflows/auditor.yml", "on: push\n")
    commit(".auditor/classification.toml", 'reviewed_by = "author-self-review"\n')
    commit(".auditor/allowlist.json", "{}\n")
    assert gen_tcb_roots.main([*args, "--check"]) == 0
    assert "D-59" in capsys.readouterr().out


@pytest.mark.parametrize("change", ["README.md", "P/M.lean", ".github/Gen.lean", ".auditor/X.lean",
                                    ".auditorx/a.toml", "uncommitted", "not_ancestor"])
def test_check_rejects_fork_with_other_changes(tmp_path, capsys, change):
    proj, args, out, commit = _fork_env(tmp_path)
    commit(".github/workflows/auditor.yml", "on: push\n")
    if change == "uncommitted":       # árvore de trabalho conta, não só o HEAD
        (proj / "P" / "M.lean").write_text("import Dep.A\ntheorem t : 1 = 1 := rfl\n", encoding="utf-8")
    elif change == "not_ancestor":    # commit irmão: difere do HEAD só em .github/, mas não é ancestral
        import subprocess
        commit(".github/side.yml", "x\n")
        side = subprocess.run(["git", "-C", str(proj), "rev-parse", "HEAD"], check=True, capture_output=True,
                              text=True).stdout.strip()
        subprocess.run(["git", "-C", str(proj), "reset", "-q", "--hard", "HEAD~1"], check=True, capture_output=True)
        d = json.loads(out.read_text(encoding="utf-8"))
        d["derived_from"]["commit"] = side
        out.write_text(gen_tcb_roots.render(d), encoding="utf-8")
    elif change == "P/M.lean":        # mesmo fecho (import inalterado): o fecho não pega, a regra pega
        commit(change, "import Dep.A\ntheorem t : 1 = 1 := rfl\n")
    else:
        commit(change, "x\n")
    assert gen_tcb_roots.main([*args, "--check"]) == 1
    assert "não é o commit fixado" in capsys.readouterr().err


def test_check_strict_when_head_is_pinned(tmp_path):
    """Sem fork, nada muda: o commit é o mesmo e a comparação é byte a byte."""
    proj, args, out, commit = _fork_env(tmp_path)
    assert gen_tcb_roots.main([*args, "--check"]) == 0
    out.write_text(out.read_text(encoding="utf-8").replace('"Lean"\n', '"Lean",\n    "Std"\n', 1),
                   encoding="utf-8")
    assert gen_tcb_roots.main([*args, "--check"]) == 1


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
