"""Teste de defasagem (decisão 6): a allow-list versionada da Etapa A precisa
corresponder exatamente ao que o toolchain fixado produz."""
import subprocess
import sys

from conftest import ROOT, require_lake


def test_allowlist_matches_pinned_toolchain():
    require_lake()
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_allowlist" / "gen.py"), "--check"],
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout + r.stderr
