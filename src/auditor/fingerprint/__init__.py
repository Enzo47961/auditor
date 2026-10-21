"""TCB enumerada e fingerprint do ambiente (componente 5; docs/tcb.md).

O fingerprint é o SHA-256 da forma canônica (JSON ordenado) de todos os componentes da
TCB mais os hashes dos metadados importados (`@[simp]`, `@[ext]`, `@[reducible]`,
`@[implemented_by]`). Mudança em qualquer componente muda o fingerprint; comparar com o
ambiente atual é responsabilidade do consumidor na Fase 0 (L-10).
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
from pathlib import Path

import auditor
from auditor import pydeps

PKG = Path(auditor.__file__).resolve().parent
REQUIRED = {
    "kernel": ("lean_version", "githash"),
    "toolchain": ("lean_toolchain",),
    "dependencies": ("lake_manifest_sha256",),
    "inspector": ("version", "source_sha256", "binary_sha256"),
    "aggregator": ("version", "source_sha256", "python", "python_dependencies"),
    "stage_a_parser": ("version", "allowlist"),
    "policy": ("version", "sha256"),
    "metadata": ("simp", "ext", "reducible", "implemented_by"),
}


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def aggregator_identity() -> dict:
    """Agregador = todo o código Python do pacote (o inspetor Lean é componente à parte)."""
    h = hashlib.sha256()
    for f in sorted(PKG.rglob("*.py")):
        rel = f.relative_to(PKG).as_posix()
        h.update(rel.encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
    try:   # D-20: o validador do schema e o que ele puxa são código confiado
        deps = pydeps.closure(pydeps.declared())
    except pydeps.DependencyError:
        deps = None                        # TCB incompleta → nenhuma `Validada`
    return {"version": auditor.__version__, "source_sha256": "sha256:" + h.hexdigest(),
            "python": platform.python_version(), "python_dependencies": deps}


def _git(root: Path, *args: str) -> str | None:
    git = shutil.which("git")
    if git is None or not (root / ".git").exists():
        return None
    p = subprocess.run([git, "-C", str(root), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else None


def dependencies(root: Path) -> dict:
    """Commit do Mathlib + hash do manifest. O Mathlib pode ser dependência (rev no manifest)
    ou o próprio projeto (commit git da raiz, quando a raiz é um repositório)."""
    raw = (root / "lake-manifest.json").read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    packages = [{"name": p.get("name"), "type": p.get("type"), "rev": p.get("rev")}
                for p in manifest.get("packages", [])]
    commit = _git(root, "rev-parse", "HEAD")
    dirty = None if commit is None else bool(_git(root, "status", "--porcelain"))
    mathlib = next((p["rev"] for p in packages if p["name"] == "mathlib"), None)
    if mathlib is None and manifest.get("name") == "mathlib":
        mathlib = commit
    return {"lake_manifest_sha256": sha256_bytes(raw), "project_package": manifest.get("name"),
            "project_commit": commit, "project_dirty": dirty, "mathlib_commit": mathlib,
            "packages": packages}


def build_tcb(sa, sb, policy, root: Path | None) -> dict:
    tcb: dict = {
        "kernel": None, "toolchain": None, "dependencies": None, "inspector": None,
        "aggregator": aggregator_identity(),
        "stage_a_parser": {"version": sa.stage_a_version, "allowlist": sa.allowlist},
        "policy": {"version": policy.version, "sha256": policy.sha256} if policy else None,
        "metadata": sb.metadata if sb else None,
        # L-26: declarado no relatório; entra no fingerprint (outra revisão = outra base de confiança)
        "classification_review_status": (sa.allowlist or {}).get("classification_review_status"),
    }
    if sb is not None and sb.toolchain:
        # sem caminhos absolutos: o fingerprint identifica o ambiente, não a máquina
        tcb["toolchain"] = {"lean_toolchain": sb.toolchain,
                            "library_roots": (sb.boundary or {}).get("trusted_roots")}
    if sb is not None and sb.inspector and sb.inspector.get("lean_version"):
        tcb["kernel"] = {"lean_version": sb.inspector["lean_version"],
                         "githash": sb.inspector.get("lean_githash")}
        tcb["inspector"] = {k: sb.inspector.get(k) for k in ("version", "source_sha256", "binary_sha256")}
    if root is not None and (root / "lake-manifest.json").is_file():
        try:
            tcb["dependencies"] = dependencies(root)
        except (OSError, ValueError):
            tcb["dependencies"] = None
    tcb["fingerprint"] = fingerprint(tcb) if is_complete(tcb, check_fp=False) else None
    return tcb


def is_complete(tcb: dict, check_fp: bool = True) -> bool:
    for comp, keys in REQUIRED.items():
        v = tcb.get(comp)
        if not isinstance(v, dict) or any(not v.get(k) for k in keys):
            return False
    return bool(tcb.get("fingerprint")) if check_fp else True


def fingerprint(tcb: dict) -> str:
    body = {k: v for k, v in tcb.items() if k != "fingerprint"}
    return sha256_bytes(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8"))
