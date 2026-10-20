"""Fecho transitivo das dependências Python instaladas do auditor.

Usado em dois lugares:
  * TCB (D-20): o validador do schema (`jsonschema` e o que ele puxa) é código confiado e
    entra em `tcb.aggregator.python_dependencies`, com versões exatas;
  * DoD "nenhuma dependência de LLM": o teste percorre o mesmo fecho, de modo que uma
    dependência transitiva nova que traga biblioteca de LLM o faz falhar.
"""
from __future__ import annotations

import re
from importlib import metadata
from typing import Callable

NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


class DependencyError(Exception):
    pass


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _installed_requires(dist: str) -> list[str] | None:
    try:
        return metadata.requires(dist) or []
    except metadata.PackageNotFoundError:
        return None


def _installed_version(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def closure(roots: list[str], requires: Callable[[str], list[str] | None] = _installed_requires,
            version: Callable[[str], str | None] = _installed_version) -> dict[str, str]:
    """{nome normalizado: versão} do fecho transitivo das distribuições instaladas.

    Requisitos de `extra` são ignorados (não instalados por padrão). Requisito com marcador
    (ex.: `python_version < "3.9"`) e não instalado é tratado como não aplicável. Requisito
    SEM marcador e não instalado → `DependencyError`: o ambiente não corresponde ao declarado."""
    out: dict[str, str] = {}
    stack = [(r, False) for r in roots]
    while stack:
        req, has_marker = stack.pop()
        m = NAME.match(req)
        if m is None:
            raise DependencyError(f"requisito ilegível: {req!r}")
        name = normalize(m.group(1))
        if name in out:
            continue
        v = version(name)
        if v is None:
            if has_marker:
                continue
            raise DependencyError(f"dependência declarada e não instalada: {name}")
        out[name] = v
        for r in requires(name) or []:
            spec, _, marker = r.partition(";")
            if "extra" in marker:
                continue
            stack.append((spec, bool(marker.strip())))
    return dict(sorted(out.items()))


def declared() -> list[str]:
    """Dependências de execução declaradas pelo pacote instalado (ou pelo pyproject, se rodando do fonte)."""
    reqs = _installed_requires("auditor")
    if reqs is not None:
        return [r for r in reqs if "extra" not in r.partition(";")[2]]
    import tomllib
    from pathlib import Path
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    return list(tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["dependencies"])
