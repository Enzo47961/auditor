"""target_trusted_roots (D-42, D-47): as raízes do toolchain cujos módulos são implicitamente
confiáveis no fecho do projeto-alvo — as que ele efetivamente usa. NÃO são "todas as raízes da
TCB do Lean": raiz declarada e não usada fica fora, e seus módulos são tratados como user-level.

Uso (manutenção, a cada subida de toolchain; docs/maintenance.md, passo 8):
    python tools/gen_tcb_roots.py --sysroot "$(lean --print-prefix)" --project <mathlib> --root Mathlib
    python tools/gen_tcb_roots.py ... --check      # confere contra o arquivo versionado (exit 1 se diverge)

O projeto precisa estar no commit fixado e com as dependências em `<packagesDir>/<nome>` nas
revisões exatas do seu `lake-manifest.json`: cada pacote `git` é conferido (`git rev-parse HEAD`
== `rev`) e a divergência é erro. A partir de todos os módulos `<root>` e `<root>.*` do projeto
(mais `Init`, importado implicitamente), percorre os cabeçalhos de import no fonte do toolchain
(`<sysroot>/src/lean`, `<sysroot>/src/lean/lake`), do projeto e dos pacotes, e conta os módulos
do toolchain alcançados por raiz. Import sem fonte encontrada é erro: o fecho seria incompleto.

Raiz da allow-list = raiz declarada pelo toolchain (`<sysroot>/lib/lean/*.olean`) que aparece no
fecho. Saída: `src/auditor/data/target_trusted_roots/<toolchain>.json`, com a procedência.
Projeto-alvo que não é o Mathlib gera o próprio arquivo com este gerador (L-21).

O SHA-256 do `lake-manifest.json` é do conteúdo com fim de linha normalizado (CRLF → LF, D-53):
o mesmo commit dá o mesmo hash num clone Windows (`core.autocrlf=true`) e no Linux.

`--check` num fork de medição (D-54, L-24): o `HEAD` pode diferir do commit gravado desde que
esse commit seja ancestral do `HEAD` e a árvore de trabalho só difira dele em `.github/`, sem
nenhum `.lean`. O resto da comparação continua estrito. Fora disso, o commit tem de ser o mesmo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "layer2"))
sys.path.insert(0, str(ROOT / "src"))
from fanout import HeaderError, header_imports  # noqa: E402

from auditor.allowlist import normalize_newlines, sanitize  # noqa: E402
from auditor.tcb_boundary import BoundaryError, package_dirs  # noqa: E402

FORMAT = 1
MEANING = ("raízes do toolchain cujos módulos são implicitamente confiáveis no fecho do projeto-alvo "
           "(as que ele usa); NÃO todas as raízes da TCB do Lean. Raiz declarada e fora desta lista: "
           "módulos user-level, regras de @[extern]/@[implemented_by] aplicadas (fail-closed).")
DATA = ROOT / "src" / "auditor" / "data" / "target_trusted_roots"


class GenError(Exception):
    pass


def _git_head(d: Path) -> str | None:
    try:
        return subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def declared_roots(sysroot: Path) -> list[str]:
    roots = sorted(p.stem for p in (sysroot / "lib" / "lean").glob("*.olean"))
    if not roots:
        raise GenError(f"toolchain não declara raízes: {sysroot / 'lib' / 'lean'}")
    return roots


def _index(base: Path, origin: str, index: dict[str, tuple[Path, str]]) -> None:
    for f in sorted(base.rglob("*.lean")):
        rel = f.relative_to(base)
        if ".lake" in rel.parts:
            continue
        index.setdefault(".".join(rel.with_suffix("").parts), (f, origin))


def generate(sysroot: Path, project: Path, root: str) -> dict:
    tc_file = project / "lean-toolchain"
    mf_file = project / "lake-manifest.json"
    if not tc_file.is_file() or not mf_file.is_file():
        raise GenError("projeto sem lean-toolchain ou lake-manifest.json")
    toolchain = tc_file.read_text(encoding="utf-8").strip()
    mf_bytes = mf_file.read_bytes()
    try:
        pkgs = package_dirs(project, json.loads(mf_bytes))
    except (BoundaryError, json.JSONDecodeError) as e:
        raise GenError(f"lake-manifest.json: {e}") from e
    revs = {p["name"]: p.get("rev") for p in json.loads(mf_bytes).get("packages", [])}
    packages = {}
    for name, d in pkgs:
        if not d.is_dir():
            raise GenError(f"pacote {name} ausente em {d} (baixe as dependências: lake exe cache get)")
        if revs.get(name) is not None:
            head = _git_head(d)
            if head != revs[name]:
                raise GenError(f"pacote {name} em {head!r}, manifest fixa {revs[name]!r}")
        packages[name] = revs.get(name) or "path"
    src = sysroot / "src" / "lean"
    if not src.is_dir():
        raise GenError(f"fonte do toolchain ausente: {src}")
    index: dict[str, tuple[Path, str]] = {}
    _index(src, "toolchain", index)
    _index(src / "lake", "toolchain", index)
    _index(project, "project", index)
    for _, d in pkgs:
        _index(d, "package", index)
    start = sorted(m for m, (_, o) in index.items() if o == "project" and (m == root or m.startswith(root + ".")))
    if not start:
        raise GenError(f"nenhum módulo {root} no projeto")
    seen, q, missing = {"Init", *start}, deque(["Init", *start]), set()
    while q:
        m = q.popleft()
        try:
            imps = header_imports(index[m][0].read_text(encoding="utf-8"))
        except HeaderError as e:
            raise GenError(f"{index[m][0]}: {e}") from e
        for i in imps:
            if i in seen:
                continue
            if i not in index:
                missing.add(i)
                continue
            seen.add(i)
            q.append(i)
    if missing:
        raise GenError(f"imports sem fonte (fecho incompleto): {sorted(missing)[:20]}")
    declared = declared_roots(sysroot)
    used = Counter(m.split(".")[0] for m in seen if index[m][1] == "toolchain")
    stray = sorted(set(used) - set(declared))
    if stray:
        raise GenError(f"módulos do toolchain sob raízes não declaradas: {stray}")
    return {
        "format": FORMAT,
        "meaning": MEANING,
        "toolchain": toolchain,
        "roots": sorted(used),
        "declared_by_toolchain": declared,
        "modules_in_closure": {r: used[r] for r in sorted(used)},
        "derived_from": {"root": root, "commit": _git_head(project),
                         "lake_manifest_sha256": hashlib.sha256(normalize_newlines(mf_bytes)).hexdigest(),
                         "packages": dict(sorted(packages.items())), "closure_modules": len(seen)},
    }


def fork_drift(project: Path, pinned: str) -> str | None:
    """Por que a árvore de trabalho de `project` não é o commit `pinned` mais só `.github/` (D-54);
    None se é. O invariante é "nenhum .lean muda"; restringir a `.github/` é o proxy estrito."""
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True,
                              encoding="utf-8")
    if git("merge-base", "--is-ancestor", pinned, "HEAD").returncode != 0:
        return f"{pinned} não é ancestral do HEAD"
    d = git("diff", "--name-only", pinned)
    if d.returncode != 0:
        return f"git diff falhou: {d.stderr.strip()}"
    changed = [f for f in d.stdout.splitlines() if f]
    outside = [f for f in changed if not f.startswith(".github/")]
    if outside:
        return f"mudanças fora de .github/: {outside[:10]}"
    lean = [f for f in changed if f.endswith(".lean")]
    if lean:
        return f"arquivos .lean mudaram: {lean[:10]}"
    return None


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gen_tcb_roots")
    ap.add_argument("--sysroot", required=True, type=Path)
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--root", required=True, help="biblioteca do projeto-alvo (ex.: Mathlib)")
    ap.add_argument("--out", type=Path, help="padrão: src/auditor/data/target_trusted_roots/<toolchain>.json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    try:
        data = generate(a.sysroot, a.project, a.root)
    except GenError as e:
        sys.stderr.write(f"gen_tcb_roots: {e}\n")
        return 2
    out = a.out or DATA / f"{sanitize(data['toolchain'])}.json"
    if a.check:
        pinned = None
        if out.is_file():
            try:
                pinned = json.loads(out.read_text(encoding="utf-8"))["derived_from"]["commit"]
            except (json.JSONDecodeError, KeyError, TypeError):
                pinned = None
        head = data["derived_from"]["commit"]
        if pinned and head and head != pinned:
            why = fork_drift(a.project, pinned)
            if why is not None:
                sys.stderr.write(f"gen_tcb_roots: HEAD {head} não é o commit fixado {pinned}: {why}\n")
                return 1
            print(f"fork de medição: HEAD {head} = {pinned} + só .github/ (D-54)")
            data["derived_from"]["commit"] = pinned
        if not out.is_file() or out.read_text(encoding="utf-8") != render(data):
            sys.stderr.write(f"gen_tcb_roots: {out} diverge do fecho calculado\n{render(data)}")
            return 1
        print(f"ok: {out} (raízes {data['roots']})")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(data))
    print(f"{out}: raízes {data['roots']} de {data['declared_by_toolchain']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
