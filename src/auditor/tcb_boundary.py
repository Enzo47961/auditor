"""Fronteira de TCB (Q7, opção a): decide se um módulo é Lean-level (TCB) ou user-level.

A fronteira é declarada por duas fontes, nenhuma delas o nome do módulo:
  * o toolchain fixado declara suas raízes de biblioteca: os `.olean` de primeiro nível
    em `<sysroot>/lib/lean` (no v4.22.0: Init, Std, Lean, Lake, LakeMain, Leanc);
  * o `lake-manifest.json` declara os pacotes do usuário; cada um, e o próprio projeto,
    contribui uma raiz de usuário `<pacote>/.lake/build/lib/lean`.

Algoritmo (`classify`), dado o caminho real do `.olean` de um módulo:
  1. se está sob uma raiz de usuário e não sob o toolchain → `user`;
  2. se está sob o toolchain e não sob raiz de usuário → `tcb` somente se
     (a) a raiz do nome do módulo é declarada pelo toolchain,
     (b) o `.olean` é exatamente `<lib>/<Módulo como caminho>.olean`, e
     (c) nenhuma raiz de usuário fornece um `.olean` para o mesmo módulo (sombreamento);
  3. qualquer outro caso → `unresolved` (fail-closed).
Documentação normativa: docs/tcb.md, seção "Fronteira de TCB".
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

TCB, USER, UNRESOLVED = "tcb", "user", "unresolved"
BUILD_LIB = Path(".lake") / "build" / "lib" / "lean"


class BoundaryError(Exception):
    """Manifest ou toolchain que não permitem declarar a fronteira: fail-closed."""


@dataclass(frozen=True)
class Boundary:
    toolchain_lib: Path
    toolchain_roots: frozenset[str]
    user_roots: tuple[Path, ...]
    packages: tuple[str, ...]


def _real(p: Path) -> Path:
    return Path(os.path.realpath(p))


def _norm(p: Path) -> str:
    return os.path.normcase(str(_real(p)))


def _under(p: Path, root: Path) -> bool:
    a, b = _norm(p), _norm(root)
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def package_dirs(project_root: Path, manifest: dict) -> list[tuple[str, Path]]:
    """Diretórios dos pacotes declarados no manifest (formato 1.x do Lake)."""
    version = str(manifest.get("version", ""))
    if not version.startswith("1."):
        raise BoundaryError(f"versão de lake-manifest não reconhecida: {version!r}")
    packages_dir = manifest.get("packagesDir", ".lake/packages")
    out = []
    for pkg in manifest.get("packages", []):
        name, kind = pkg.get("name"), pkg.get("type")
        if not isinstance(name, str) or not name:
            raise BoundaryError(f"pacote sem nome no manifest: {pkg!r}")
        if kind == "git":
            out.append((name, project_root / packages_dir / name))
        elif kind == "path":
            if not isinstance(pkg.get("dir"), str):
                raise BoundaryError(f"pacote path sem 'dir': {name}")
            out.append((name, project_root / pkg["dir"]))
        else:
            raise BoundaryError(f"tipo de pacote não reconhecido: {name}: {kind!r}")
    return out


def load_boundary(project_root: Path, sysroot: Path) -> Boundary:
    lib = sysroot / "lib" / "lean"
    if not lib.is_dir():
        raise BoundaryError(f"biblioteca do toolchain ausente: {lib}")
    roots = frozenset(p.stem for p in lib.glob("*.olean"))
    if not roots:
        raise BoundaryError(f"toolchain não declara raízes de biblioteca: {lib}")
    mf = project_root / "lake-manifest.json"
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise BoundaryError(f"lake-manifest.json ilegível: {e}") from e
    pkgs = package_dirs(project_root, manifest)
    user = [project_root / BUILD_LIB, *(d / BUILD_LIB for _, d in pkgs)]
    return Boundary(_real(lib), roots, tuple(_real(u) for u in user), tuple(n for n, _ in pkgs))


def module_relpath(module: str) -> Path:
    return Path(*module.split(".")).with_suffix(".olean")


def classify(b: Boundary, module: str, olean: str | Path | None) -> tuple[str, str]:
    """(nível, razão). Nunca devolve `tcb` sem as três condições do passo 2."""
    if not olean:
        return UNRESOLVED, "olean_not_found"
    p = Path(olean)
    in_user = [r for r in b.user_roots if _under(p, r)]
    in_tc = _under(p, b.toolchain_lib)
    if in_user and not in_tc:
        return USER, "user_root"
    if in_tc and not in_user:
        rel = module_relpath(module)
        if module.split(".")[0] not in b.toolchain_roots:
            return UNRESOLVED, "module_root_not_declared_by_toolchain"
        if _norm(p) != _norm(b.toolchain_lib / rel):
            return UNRESOLVED, "olean_path_does_not_match_module"
        if any((r / rel).exists() for r in b.user_roots):
            return UNRESOLVED, "module_shadowed_by_user_package"
        return TCB, "toolchain_root"
    return UNRESOLVED, "olean_outside_declared_roots" if not in_user else "olean_in_overlapping_roots"


def unrecognized_search_path(b: Boundary, entries: list[str]) -> list[str]:
    """Entradas do search path do inspetor que não são nem o toolchain nem raízes do manifest."""
    known = [b.toolchain_lib, *b.user_roots]
    return [e for e in entries if not any(_norm(Path(e)) == _norm(k) for k in known)]
