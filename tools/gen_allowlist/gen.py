"""Gera a allow-list da Etapa A para um toolchain.

Uso: python tools/gen_allowlist/gen.py [--toolchain-file lean-toolchain] [--check]

A lista de comandos vem do próprio Lean (categoria `command` do parser, via
Dump.lean, compilado contra o toolchain informado). Nenhuma versão é codificada
aqui: o toolchain vem do arquivo. `--check` não escreve; falha (exit 1) se o
arquivo versionado divergir do que o toolchain produz — é o teste de defasagem.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import shutil
import tempfile
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT_DIR = ROOT / "src" / "auditor" / "data" / "allowlist"
GENERATOR_VERSION = "1"


def sanitize(toolchain: str) -> str:
    return toolchain.replace("/", "__").replace(":", "__")


def extract_commands(toolchain: str) -> list[str]:
    """Compila Dump.lean numa cópia temporária (sem artefatos no repositório)."""
    with tempfile.TemporaryDirectory(prefix="gen_allowlist_") as tmp:
        work = Path(tmp)
        for name in ("Dump.lean", "lakefile.lean"):
            shutil.copy(HERE / name, work / name)
        (work / "lean-toolchain").write_text(toolchain + "\n")
        subprocess.run(["lake", "build"], cwd=work, check=True, capture_output=True)
        out = subprocess.run(["lake", "exe", "dump"], cwd=work, check=True,
                             capture_output=True, text=True).stdout
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def build(toolchain: str) -> dict:
    cls = tomllib.loads((HERE / "classification.toml").read_text(encoding="utf-8"))
    commands = extract_commands(toolchain)
    known = set(commands)
    for key in ("syntax_extension", "metaprogramming"):
        stale = set(cls[key]) - known
        if stale:
            sys.exit(f"classification.toml cita comandos inexistentes em {toolchain}: {sorted(stale)}")
    risky = set(cls["syntax_extension"]) | set(cls["metaprogramming"])
    return {
        "toolchain": toolchain,
        "generator_version": GENERATOR_VERSION,
        "classification_version": cls["classification_version"],
        "extracted_command_count": len(commands),
        "allowed": sorted(known - risky),
        "syntax_extension": sorted(cls["syntax_extension"]),
        "metaprogramming": sorted(cls["metaprogramming"]),
        "continuation": cls["continuation"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--toolchain-file", default=str(ROOT / "lean-toolchain"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    toolchain = Path(a.toolchain_file).read_text().strip()
    data = build(toolchain)
    path = OUT_DIR / f"{sanitize(toolchain)}.json"
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if a.check:
        if not path.exists() or path.read_text(encoding="utf-8") != rendered:
            print(f"DEFASADA: {path.name} não corresponde ao toolchain {toolchain}", file=sys.stderr)
            return 1
        print(f"ok: {path.name}")
        return 0
    path.write_text(rendered, encoding="utf-8")
    print(f"escrito: {path.relative_to(ROOT)} ({data['extracted_command_count']} comandos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
