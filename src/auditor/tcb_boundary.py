"""Fronteira de TCB (Q7, opção a): decide se um módulo é Lean-level (TCB) ou user-level.

A fronteira é declarada por duas fontes, nenhuma delas o nome do módulo:
  * o toolchain fixado declara suas raízes de biblioteca: os `.olean` de primeiro nível
    em `<sysroot>/lib/lean`; delas, só as que o projeto-alvo usa são TCB (D-42): a allow-list
    `data/tcb_roots/<toolchain>.json`, gerada por `tools/gen_tcb_roots.py` a partir do fecho de
    imports do Mathlib fixado e conferida contra as raízes declaradas (drift → fail-closed);
  * o `lake-manifest.json` declara os pacotes do usuário; cada um, e o próprio projeto,
    contribui uma raiz de usuário `<pacote>/.lake/build/lib/lean`.

Algoritmo (`classify`), dado o caminho real do `.olean` de um módulo:
  1. se está sob uma raiz de usuário e não sob o toolchain → `user`;
  2. se está sob o toolchain e não sob raiz de usuário → `tcb` somente se
     (a) a raiz do nome do módulo é declarada pelo toolchain e está na allow-list de raízes,
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
TCB_ROOTS_DIR = Path(__file__).resolve().parent / "data" / "tcb_roots"
TCB_ROOTS_FORMAT = 1


class BoundaryError(Exception):
    """Manifest ou toolchain que não permitem declarar a fronteira: fail-closed."""


@dataclass(frozen=True)
class Boundary:
    toolchain_lib: Path
    toolchain_roots: frozenset[str]      # raízes TCB: declaradas pelo toolchain ∩ allow-list (D-42)
    user_roots: tuple[Path, ...]
    packages: tuple[str, ...]
    declared_roots: frozenset[str] = frozenset()   # tudo o que o toolchain declara


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


def load_tcb_roots(toolchain: str) -> dict:
    """Allow-list de raízes de TCB do toolchain (D-42). Ausente ou malformada → BoundaryError."""
    p = TCB_ROOTS_DIR / f"{toolchain.replace('/', '__').replace(':', '__')}.json"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise BoundaryError(f"allow-list de raízes de TCB indisponível para {toolchain!r}: {e}") from e
    if not isinstance(data, dict) or data.get("format") != TCB_ROOTS_FORMAT \
            or not all(isinstance(data.get(k), list) and all(isinstance(r, str) for r in data[k])
                       for k in ("roots", "declared_by_toolchain")):
        raise BoundaryError(f"allow-list de raízes de TCB malformada: {p}")
    if data.get("toolchain") != toolchain:
        raise BoundaryError(f"allow-list de raízes de TCB declara {data.get('toolchain')!r}, projeto fixa {toolchain!r}")
    return data


def load_boundary(project_root: Path, sysroot: Path, tcb_roots: dict | None = None) -> Boundary:
    """`tcb_roots`: allow-list já carregada (testes); padrão: a do `lean-toolchain` do projeto."""
    lib = sysroot / "lib" / "lean"
    if not lib.is_dir():
        raise BoundaryError(f"biblioteca do toolchain ausente: {lib}")
    declared = frozenset(p.stem for p in lib.glob("*.olean"))
    if not declared:
        raise BoundaryError(f"toolchain não declara raízes de biblioteca: {lib}")
    if tcb_roots is None:
        try:
            toolchain = (project_root / "lean-toolchain").read_text(encoding="utf-8").strip()
        except OSError as e:
            raise BoundaryError(f"lean-toolchain ilegível: {e}") from e
        tcb_roots = load_tcb_roots(toolchain)
    if sorted(declared) != sorted(tcb_roots["declared_by_toolchain"]):
        raise BoundaryError(f"raízes declaradas pelo toolchain {sorted(declared)} ≠ as da allow-list "
                            f"{sorted(tcb_roots['declared_by_toolchain'])} (regenerar: tools/gen_tcb_roots.py)")
    roots = frozenset(tcb_roots["roots"])
    if not roots <= declared:
        raise BoundaryError(f"raízes da allow-list não declaradas pelo toolchain: {sorted(roots - declared)}")
    mf = project_root / "lake-manifest.json"
    try:
        manifest = json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise BoundaryError(f"lake-manifest.json ilegível: {e}") from e
    pkgs = package_dirs(project_root, manifest)
    user = [project_root / BUILD_LIB, *(d / BUILD_LIB for _, d in pkgs)]
    return Boundary(_real(lib), roots, tuple(_real(u) for u in user), tuple(n for n, _ in pkgs), declared)


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
        if module.split(".")[0] not in b.declared_roots:
            return UNRESOLVED, "module_root_not_declared_by_toolchain"
        if module.split(".")[0] not in b.toolchain_roots:
            return UNRESOLVED, "module_root_not_used_by_target_project"
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
