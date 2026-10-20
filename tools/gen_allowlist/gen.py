"""Gera a allow-list do CORE da Etapa A para um toolchain.

Uso: python tools/gen_allowlist/gen.py [--toolchain-file lean-toolchain] [--check]

A lista de comandos vem do próprio Lean (categoria `command` do parser, via
`src/auditor/lean/Dump.lean`, rodado com o toolchain informado). Nenhuma versão é
codificada aqui: o toolchain vem do arquivo. `--check` não escreve; falha (exit 1)
se o arquivo versionado divergir do que o toolchain produz — é o teste de defasagem.

Allow-lists de PROJETO (ex.: Mathlib) são geradas por `auditor-gen-allowlist --project`.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from auditor.allowlist import AllowlistError, core_path, extract_core, render  # noqa: E402

GENERATOR_VERSION = "1"


def build(toolchain: str) -> dict:
    cls = tomllib.loads((HERE / "classification.toml").read_text(encoding="utf-8"))
    commands = extract_core(toolchain)
    known = set(commands)
    for key in ("syntax_extension", "metaprogramming"):
        stale = set(cls[key]) - known
        if stale:
            sys.exit(f"classification.toml cita comandos inexistentes em {toolchain}: {sorted(stale)}")
    risky = set(cls["syntax_extension"]) | set(cls["metaprogramming"])
    return {
        "kind": "core",
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
    toolchain = Path(a.toolchain_file).read_text(encoding="utf-8").strip()
    try:
        data = build(toolchain)
    except AllowlistError as e:
        print(e, file=sys.stderr)
        return 2
    path = core_path(toolchain)
    rendered = render(data)
    if a.check:
        if not path.exists() or path.read_bytes() != rendered.encode("utf-8"):
            print(f"DEFASADA: {path.name} não corresponde ao toolchain {toolchain}", file=sys.stderr)
            return 1
        print(f"ok: {path.name}")
        return 0
    path.write_bytes(rendered.encode("utf-8"))
    print(f"escrito: {path.relative_to(ROOT)} ({data['extracted_command_count']} comandos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
