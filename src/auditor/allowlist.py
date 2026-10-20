"""Allow-list de comandos da Etapa A: extração e pino do ambiente.

Dois tipos de allow-list:
  * `core`    — comandos do toolchain (`import Lean`). Empacotada em
                `data/allowlist/<toolchain>.json`, gerada por `tools/gen_allowlist/gen.py`.
  * `project` — comandos do toolchain + os definidos pelo projeto e suas dependências
                (ex.: `lemma` no Mathlib). Gerada por `auditor-gen-allowlist --project <dir>`
                e gravada em `<dir>/.auditor/allowlist.json`.

A allow-list de projeto é vinculada ao pino do ambiente (`env_pin`: `lean-toolchain` +
`lake-manifest.json`). A Etapa A só a usa se o pino bater com o ambiente atual; senão,
`allowlist_stale` (fail-closed). Comando do projeto sem classificação explícita cai em
`unclassified`, que é fail-closed — ao contrário do core, onde o critério de
`classification.toml` foi aplicado a todos os comandos extraídos.

Nenhuma versão de Lean ou de dependência é codificada aqui: tudo vem do projeto.
O pino NÃO cobre o código-fonte do próprio projeto nem a correção semântica da
classificação (limitations.md, L-16).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

GENERATOR_VERSION = "2"
ENV_PIN_VERSION = "1"
PKG = Path(__file__).resolve().parent
DUMP = PKG / "lean" / "Dump.lean"
CORE_DIR = PKG / "data" / "allowlist"
PROJECT_REL = Path(".auditor") / "allowlist.json"
PROJECT_CLASSIFICATION_REL = Path(".auditor") / "classification.toml"
CLASS_KEYS = ("allowed", "syntax_extension", "metaprogramming")


class AllowlistError(Exception):
    pass


def env_pin(toolchain: str, manifest: bytes) -> str:
    """Pino do ambiente para allow-lists de projeto: toolchain exato + bytes do manifesto."""
    h = hashlib.sha256()
    for part in (f"auditor-env-pin-v{ENV_PIN_VERSION}".encode(), toolchain.encode("utf-8"), manifest):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return "sha256:" + h.hexdigest()


def sanitize(toolchain: str) -> str:
    return toolchain.replace("/", "__").replace(":", "__")


def core_path(toolchain: str) -> Path:
    return CORE_DIR / f"{sanitize(toolchain)}.json"


def _lake() -> str:
    lake = shutil.which("lake")
    if lake is None:
        raise AllowlistError("`lake` não encontrado no PATH")
    return lake


def run_dump(cwd: Path, modules: list[str], use_lake_env: bool) -> list[str]:
    """Roda o extrator no ambiente de `cwd` (o `lean-toolchain` de `cwd` seleciona o Lean)."""
    with tempfile.TemporaryDirectory(prefix="auditor_dump_") as tmp:
        dump = Path(tmp) / "Dump.lean"
        shutil.copy(DUMP, dump)
        args = [str(dump)]
        if modules:
            mods = Path(tmp) / "modules.txt"
            mods.write_text("\n".join(modules) + "\n", encoding="utf-8")
            args.append(str(mods))
        if use_lake_env:
            cmd = [_lake(), "env", "lean", "--run", *args]
        elif shutil.which("lean") is None:
            raise AllowlistError("`lean` não encontrado no PATH")
        else:
            cmd = ["lean", "--run", *args]
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if p.returncode != 0:
        raise AllowlistError(f"extrator falhou (exit {p.returncode}): {p.stdout}{p.stderr}")
    return sorted({line.strip() for line in p.stdout.splitlines() if line.strip()})


def extract_core(toolchain: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="auditor_core_") as tmp:
        (Path(tmp) / "lean-toolchain").write_text(toolchain + "\n", encoding="utf-8")
        return run_dump(Path(tmp), [], use_lake_env=False)


def project_modules(project: Path) -> list[str]:
    """Módulos do próprio projeto: os `.olean` produzidos pelo `lake build` do projeto."""
    lib = project / ".lake" / "build" / "lib" / "lean"
    if not lib.is_dir():
        raise AllowlistError(f"nenhum build encontrado em {lib}")
    mods = sorted(".".join(p.relative_to(lib).with_suffix("").parts) for p in lib.rglob("*.olean"))
    if not mods:
        raise AllowlistError(f"nenhum .olean em {lib}")
    return mods


def load_core(toolchain: str) -> dict:
    p = core_path(toolchain)
    if not p.is_file():
        raise AllowlistError(f"sem allow-list do core para {toolchain}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("toolchain") != toolchain or data.get("kind") != "core":
        raise AllowlistError(f"allow-list do core inconsistente: {p.name}")
    return data


def build_project(project: Path, classification: Path | None) -> dict:
    project = project.resolve()
    tc_file, manifest = project / "lean-toolchain", project / "lake-manifest.json"
    if not tc_file.is_file() or not manifest.is_file():
        raise AllowlistError("projeto sem lean-toolchain ou lake-manifest.json: ambiente não fixado")
    toolchain = tc_file.read_text(encoding="utf-8").strip()
    core = load_core(toolchain)

    b = subprocess.run([_lake(), "build"], cwd=project, capture_output=True, text=True, encoding="utf-8")
    if b.returncode != 0:
        raise AllowlistError(f"lake build falhou: {b.stdout}{b.stderr}")
    modules = project_modules(project)
    extracted = set(run_dump(project, modules, use_lake_env=True))

    core_cmds = set().union(*(core[k] for k in CLASS_KEYS))
    missing = core_cmds - extracted
    if missing:
        raise AllowlistError(f"allow-list do core não corresponde ao ambiente do projeto: {sorted(missing)}")
    new = extracted - core_cmds

    cls_path = classification or (project / PROJECT_CLASSIFICATION_REL)
    cls: dict = {"classification_version": None, **{k: [] for k in CLASS_KEYS}}
    cls_sha = None
    if cls_path.is_file():
        raw = cls_path.read_bytes()
        cls_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        cls = {**cls, **tomllib.loads(raw.decode("utf-8"))}
        unknown_keys = set(cls) - {"classification_version", *CLASS_KEYS}
        if unknown_keys:
            raise AllowlistError(f"classificação com chaves desconhecidas: {sorted(unknown_keys)}")
        listed = [c for k in CLASS_KEYS for c in cls[k]]
        dup = {c for c in listed if listed.count(c) > 1}
        if dup:
            raise AllowlistError(f"comando classificado mais de uma vez: {sorted(dup)}")
        stale = set(listed) - new
        if stale:
            raise AllowlistError(f"classificação cita comandos que não são do projeto: {sorted(stale)}")
    elif classification is not None:
        raise AllowlistError(f"classificação não encontrada: {classification}")

    classified = set().union(*(set(cls[k]) for k in CLASS_KEYS))
    return {
        "kind": "project",
        "toolchain": toolchain,
        "env_pin": env_pin(toolchain, manifest.read_bytes()),
        "generator_version": GENERATOR_VERSION,
        "classification_version": core["classification_version"],
        "core_generator_version": core["generator_version"],
        "project_classification_version": cls["classification_version"],
        "project_classification_sha256": cls_sha,
        "module_count": len(modules),
        "extracted_command_count": len(extracted),
        "allowed": sorted(set(core["allowed"]) | set(cls["allowed"])),
        "syntax_extension": sorted(set(core["syntax_extension"]) | set(cls["syntax_extension"])),
        "metaprogramming": sorted(set(core["metaprogramming"]) | set(cls["metaprogramming"])),
        "continuation": core["continuation"],
        "unclassified": sorted(new - classified),
    }


def render(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="auditor-gen-allowlist",
                                 description="Gera a allow-list da Etapa A para um projeto Lake.")
    ap.add_argument("--project", required=True, type=Path)
    ap.add_argument("--classification", type=Path,
                    help=f"padrão: <projeto>/{PROJECT_CLASSIFICATION_REL.as_posix()}")
    ap.add_argument("--output", type=Path, help=f"padrão: <projeto>/{PROJECT_REL.as_posix()}")
    ap.add_argument("--check", action="store_true",
                    help="não escreve; exit 1 se o arquivo existente divergir do ambiente atual")
    a = ap.parse_args(argv)
    out = a.output or (a.project / PROJECT_REL)
    try:
        data = build_project(a.project, a.classification)
    except AllowlistError as e:
        print(f"auditor-gen-allowlist: {e}", file=sys.stderr)
        return 2
    rendered = render(data)
    if a.check:
        if not out.is_file() or out.read_bytes() != rendered.encode("utf-8"):
            print(f"DEFASADA: {out}", file=sys.stderr)
            return 1
        print(f"ok: {out}")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(rendered.encode("utf-8"))
    print(f"escrito: {out} ({data['extracted_command_count']} comandos, "
          f"{len(data['unclassified'])} sem classificação)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
