"""CLI: exit codes de infraestrutura e o caminho de timeout (fail-closed, nunca sucesso)."""
import json
import os
import shutil
import subprocess
import sys

from conftest import CONFORMANCE, DEFAULT_POLICY, ROOT, run_auditor


def cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, "-m", "auditor", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


def test_missing_file_is_infra(tmp_path):
    p = cli("check", str(tmp_path / "nope.lean"), "--output", str(tmp_path / "r.json"),
            "--policy", str(DEFAULT_POLICY))
    assert p.returncode == 2


def test_bad_arguments_are_infra():
    assert cli("check").returncode == 2


def test_artificial_timeout_never_success(tmp_path):
    """L-11: limite artificial; o relatório declara `timeout_test: artificial`, exit 2."""
    proj = tmp_path / "p"
    shutil.copytree(CONFORMANCE / "01-sorry-target", proj, ignore=shutil.ignore_patterns(".lake"))
    out = tmp_path / "r.json"
    p = cli("check", str(proj / "Fixture" / "Target.lean"), "--output", str(out),
            "--policy", str(DEFAULT_POLICY), "--timeout-file", "0.01", "--timeout-test", "artificial")
    assert p.returncode == 2, p.stderr
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["execution_metadata"]["timeout_test"] == "artificial"
    assert r["compilation"]["status"] == "timeout"
    assert [x["code"] for x in r["infrastructure"]["reasons"]] == ["timeout"]
    assert all(d["overall_status"] == "unresolved" for d in r["declarations"])


def test_stale_project_allowlist_is_infra(tmp_path):
    proj = tmp_path / "p"
    shutil.copytree(CONFORMANCE / "01-sorry-target", proj, ignore=shutil.ignore_patterns(".lake"))
    (proj / ".auditor").mkdir()
    (proj / ".auditor" / "allowlist.json").write_text('{"kind": "project"}', encoding="utf-8")
    r = run_auditor(proj / "Fixture" / "Target.lean", tmp_path)
    assert r.exit_code == 2
    assert "allowlist_stale" in [x["code"] for x in r.report["infrastructure"]["reasons"]]
    assert all(d["overall_status"] != "verified" for d in r.report["declarations"])


def test_seal_declares_what_was_not_verified(tmp_path):
    r = run_auditor(CONFORMANCE / "06-tcb-boundary" / "Fixture" / "Target.lean", tmp_path)
    for d in r.report["declarations"]:
        assert "Correspondência: Não Auditada" in d["seal"]
        assert "Não coberto: correspondência, kernel" in d["seal"]
        assert d["tcb"]["fingerprint"] in d["seal"]


def test_empty_file_e2e(tmp_path):
    """D-15 fim a fim: arquivo só com documentação → exit 2; com --allow-empty → exit 0."""
    proj = tmp_path / "p"
    shutil.copytree(CONFORMANCE / "01-sorry-target", proj, ignore=shutil.ignore_patterns(".lake"))
    target = proj / "Fixture" / "Target.lean"
    target.write_text("/-! Só documentação, nenhuma declaração. -/\n", encoding="utf-8")
    out = tmp_path / "r.json"
    base = ["check", str(target), "--output", str(out), "--policy", str(DEFAULT_POLICY)]
    p = cli(*base)
    assert p.returncode == 2, p.stderr
    r = json.loads(out.read_text(encoding="utf-8"))
    assert [x["code"] for x in r["infrastructure"]["reasons"]] == ["no_declarations_found"]
    assert cli(*base, "--allow-empty").returncode == 0


def test_timeout_file_default_is_90_and_timeout_is_alias(tmp_path, monkeypatch):
    """Instrução 11 (D-21): o timeout por arquivo tem padrão de 90 s; `--timeout` é sinônimo."""
    import auditor.__main__ as m
    seen = []
    monkeypatch.setattr(m, "check", lambda a: seen.append(a.timeout) or 0)
    base = ["check", "T.lean", "--output", "r.json", "--policy", "p.toml"]
    m.main(base)
    m.main(base + ["--timeout", "12"])
    m.main(base + ["--timeout-file", "7"])
    assert seen == [90.0, 12.0, 7.0]
