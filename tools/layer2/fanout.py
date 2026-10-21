"""Fanout de módulos de um projeto Lake: quantos módulos do projeto importam cada módulo,
direta ou transitivamente (fecho reverso do grafo de imports).

Uso (camada 2, escolha do "arquivo de maior fanout" de forma mecânica e reprodutível):
    python tools/layer2/fanout.py <raiz-do-projeto> --root Mathlib [--top 20] [--json saida.json]
        [--expect-commit <sha>]

Lê só o cabeçalho de imports de cada `.lean` sob `<raiz>/<root>/` (e `<raiz>/<root>.lean`):
comentários, `prelude`, `module` e linhas `import` (com modificadores `public`/`meta`/`private`
antes e `all` depois do `import`). O primeiro comando de outro tipo encerra o cabeçalho. Imports
fora do projeto (Init, Std, Lean, dependências) não entram no grafo. Determinístico: empates são
ordenados pelo nome. Não acessa a rede: o resultado é função do checkout, cuja procedência
(commit, SHA-256 do lake-manifest.json, lean-toolchain) vai na saída JSON (docs/ci.md, D-38 (d)).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

IMPORT = re.compile(r"^(?:(?:public|meta|private)\s+)*import\s+(.*)$")
MODULE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*$")


class HeaderError(Exception):
    pass


def header_imports(text: str) -> list[str]:
    out, depth = [], 0
    for raw in text.splitlines():
        line = raw
        while line:
            if depth:
                i, j = line.find("/-"), line.find("-/")
                if j < 0 and i < 0:
                    line = ""
                elif i >= 0 and (j < 0 or i < j):
                    depth, line = depth + 1, line[i + 2:]
                else:
                    depth, line = depth - 1, line[j + 2:]
                continue
            s = line.strip()
            if not s or s.startswith("--"):
                line = ""
            elif s.startswith("/-"):
                depth, line = 1, s[2:]
            elif s == "prelude" or s == "module":
                line = ""
            elif m := IMPORT.match(s):
                rest = m.group(1).split("--", 1)[0]
                if "/-" in rest:
                    raise HeaderError(f"comentário de bloco dentro de import: {raw!r}")
                names = rest.split()
                if names[:1] == ["all"]:           # `import all M`: M com as definições privadas
                    names = names[1:]
                for name in names:
                    if not MODULE_NAME.match(name):
                        raise HeaderError(f"nome de módulo ilegível: {name!r}")
                    out.append(name)
                line = ""
            else:
                return out
    return out


def module_of(path: Path, project: Path) -> str:
    return ".".join(path.relative_to(project).with_suffix("").parts)


def graph(project: Path, root: str) -> dict[str, list[str]]:
    files = sorted((project / root).rglob("*.lean"))
    if (project / f"{root}.lean").is_file():
        files.append(project / f"{root}.lean")
    mods = {module_of(f, project): f for f in files}
    return {m: sorted({i for i in header_imports(f.read_text(encoding="utf-8")) if i in mods})
            for m, f in mods.items()}


def _reach(adj: dict[str, list[str]], start: str) -> int:
    seen, q = set(), deque(adj[start])
    while q:
        x = q.popleft()
        if x not in seen:
            seen.add(x)
            q.extend(adj[x])
    return len(seen)


def fanout(g: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    """`direct`/`transitive`: dependentes (fecho reverso); `imports_transitive`: fecho direto,
    que é o que pesa no custo da auditoria do próprio arquivo (docs/ci.md, D-38)."""
    rev: dict[str, list[str]] = {m: [] for m in g}
    for m, imps in g.items():
        for i in imps:
            rev[i].append(m)
    return {m: {"direct": len(rev[m]), "transitive": _reach(rev, m), "imports_transitive": _reach(g, m)}
            for m in g}


def provenance(project: Path) -> dict:
    """De onde veio o checkout: sem isso, o ranking não é atribuível a um commit."""
    def read(name: str) -> bytes | None:
        p = project / name
        return p.read_bytes() if p.is_file() else None
    try:
        commit = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], capture_output=True,
                                text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    mf, tc = read("lake-manifest.json"), read("lean-toolchain")
    return {"commit": commit, "lake_manifest_sha256": hashlib.sha256(mf).hexdigest() if mf is not None else None,
            "lean_toolchain": tc.decode("utf-8").strip() if tc is not None else None}


def ranking(project: Path, root: str) -> list[dict]:
    fo = fanout(graph(project, root))
    rows = [{"module": m, "file": str(Path(*m.split(".")).with_suffix(".lean")).replace("\\", "/"), **v}
            for m, v in fo.items()]
    return sorted(rows, key=lambda r: (-r["transitive"], -r["direct"], r["module"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fanout")
    ap.add_argument("project")
    ap.add_argument("--root", required=True, help="biblioteca do projeto (ex.: Mathlib)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--json")
    ap.add_argument("--expect-commit", help="falha (exit 2) se o checkout não estiver neste commit")
    a = ap.parse_args(argv)
    prov = provenance(Path(a.project))
    if a.expect_commit and prov["commit"] != a.expect_commit:
        sys.stderr.write(f"fanout: checkout em {prov['commit']!r}, esperado {a.expect_commit!r}\n")
        return 2
    try:
        rows = ranking(Path(a.project), a.root)
    except HeaderError as e:
        sys.stderr.write(f"fanout: {e}\n")
        return 2
    if a.json:
        Path(a.json).write_text(json.dumps({"provenance": prov, "rows": rows}, ensure_ascii=False, indent=2)
                                + "\n", encoding="utf-8")
    print(f"commit {prov['commit']}; lake-manifest.json sha256 {prov['lake_manifest_sha256']}; "
          f"{prov['lean_toolchain']}")
    print(f"{len(rows)} módulos em {a.root}")
    print("| Módulo | Arquivo | Dependentes diretos | Dependentes transitivos | Imports transitivos |\n"
          "|---|---|---|---|---|")
    for r in rows[:a.top]:
        print(f"| `{r['module']}` | `{r['file']}` | {r['direct']} | {r['transitive']} | {r['imports_transitive']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
