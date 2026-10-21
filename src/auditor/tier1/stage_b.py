"""Etapa B — inspeção das declarações elaboradas.

Contrato (mesmo da Etapa A):
  * NUNCA emite conclusão positiva. `StageBResult` não tem campo de "ok"/"passou".
    Produz fatos brutos do inspetor (`declarations`), anomalias por declaração
    (`anomalies`, que o agregador converte em fail-closed) e entradas não
    reconhecidas no nível do arquivo (`unrecognized`).
  * Não aplica política. Saber que `sorryAx` é proibido, que um axioma é
    desconhecido ou que uma justificativa é válida é papel do agregador.
  * O inspetor (`lean/Inspect.lean`) é compilado com o toolchain do projeto-alvo,
    porque `.olean` só é legível pela mesma versão do Lean. O binário fica em
    cache, identificado pelo hash do fonte + toolchain.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from auditor import tcb_boundary as tb

STAGE_B_VERSION = "1"
INSPECTOR_VERSION = "4"            # deve bater com `inspectorVersion` em Inspect.lean
PKG = Path(__file__).resolve().parent.parent
INSPECT_SRC = PKG / "lean" / "Inspect.lean"
INSPECTOR_LAKEFILE = """import Lake
open Lake DSL
package auditor_inspector
@[default_target] lean_exe inspect where
  root := `Inspect
  supportInterpreter := true
"""
MODULE_COMPONENT = re.compile(r"^[^\s.\\/]+$")


@dataclass
class StageBResult:
    file: str
    project_root: str | None = None
    module: str | None = None
    toolchain: str | None = None
    stage_b_version: str = STAGE_B_VERSION
    build: dict = field(default_factory=lambda: {"status": "not_run"})
    inspector: dict | None = None
    declarations: list[dict] = field(default_factory=list)
    anomalies: list[dict] = field(default_factory=list)      # {declaration, code, detail}
    unrecognized: list[dict] = field(default_factory=list)   # {code, detail}
    owners: dict = field(default_factory=dict)                 # dona → {docstring, module}
    boundary: dict | None = None                               # fronteira de TCB usada (Q7)
    metadata: dict | None = None                               # hashes e contagens


class InspectorBuildError(Exception):
    pass


# --------------------------------------------------------------------------- ambiente

def find_project(target: Path) -> Path | None:
    """Raiz do projeto: primeiro ancestral com `lean-toolchain` e um lakefile."""
    for d in [target.parent, *target.parent.parents]:
        if (d / "lean-toolchain").is_file() and \
                ((d / "lakefile.lean").is_file() or (d / "lakefile.toml").is_file()):
            return d
    return None


def module_name(target: Path, root: Path) -> str | None:
    try:
        rel = target.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if rel.suffix != ".lean":
        return None
    parts = rel.with_suffix("").parts
    if not parts or not all(MODULE_COMPONENT.match(p) for p in parts):
        return None
    return ".".join(parts)


def expected_lean_version(toolchain: str) -> str | None:
    """`leanprover/lean4:v4.22.0` → `4.22.0`. Formato não reconhecido → None (fail-closed)."""
    m = re.fullmatch(r"leanprover/lean4:v(\d+\.\d+\.\d+(?:-rc\d+)?)", toolchain)
    return m.group(1) if m else None


def _cache_root() -> Path:
    if env := os.environ.get("AUDITOR_CACHE"):
        return Path(env)
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "auditor"


def sha256_file(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def inspector_identity(toolchain: str) -> tuple[str, str]:
    src = INSPECT_SRC.read_bytes()
    h = hashlib.sha256()
    for part in (src, toolchain.encode("utf-8"), INSPECTOR_LAKEFILE.encode("utf-8")):
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return "sha256:" + hashlib.sha256(src).hexdigest(), h.hexdigest()[:24]


def ensure_inspector(toolchain: str, lake: str) -> dict:
    """Compila (ou reutiliza do cache) o inspetor para o toolchain. Retorna identidade + caminho."""
    src_hash, key = inspector_identity(toolchain)
    root = _cache_root() / "inspector"
    final = root / key
    exe = final / ".lake" / "build" / "bin" / ("inspect.exe" if os.name == "nt" else "inspect")
    if not exe.is_file():
        root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix=f"{key}.tmp", dir=root))
        try:
            shutil.copy(INSPECT_SRC, work / "Inspect.lean")
            (work / "lakefile.lean").write_bytes(INSPECTOR_LAKEFILE.encode("utf-8"))
            (work / "lean-toolchain").write_bytes((toolchain + "\n").encode("utf-8"))
            p = subprocess.run([lake, "build"], cwd=work, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
            if p.returncode != 0:
                raise InspectorBuildError(p.stdout[-4000:] + p.stderr[-4000:])
            try:
                work.rename(final)
            except OSError:          # outro processo venceu a corrida: usa o dele
                shutil.rmtree(work, ignore_errors=True)
        finally:
            if work.exists() and work != final:
                shutil.rmtree(work, ignore_errors=True)
    if not exe.is_file():
        raise InspectorBuildError(f"binário do inspetor ausente após build: {exe}")
    return {"version": INSPECTOR_VERSION, "source_sha256": src_hash,
            "binary_sha256": sha256_file(exe), "path": str(exe)}


# --------------------------------------------------------------------------- análise

def analyze(target: Path, timeout_s: float = 90.0) -> StageBResult:
    target = Path(target)
    res = StageBResult(file=str(target))
    started = time.monotonic()

    def remaining() -> float:
        return max(1.0, timeout_s - (time.monotonic() - started))

    root = find_project(target)
    if root is None:
        res.unrecognized.append({"code": "environment_unpinned",
                                 "detail": "projeto Lake com lean-toolchain não encontrado"})
        return res
    res.project_root = str(root)
    res.toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
    if not (root / "lake-manifest.json").is_file():
        res.unrecognized.append({"code": "environment_unpinned", "detail": "lake-manifest.json ausente"})
        return res
    res.module = module_name(target, root)
    if res.module is None:
        res.unrecognized.append({"code": "module_unresolved",
                                 "detail": "caminho do arquivo não corresponde a um módulo do projeto"})
        return res
    expected = expected_lean_version(res.toolchain)
    if expected is None:
        res.unrecognized.append({"code": "toolchain_unrecognized", "detail": res.toolchain})
        return res
    lake = shutil.which("lake")
    if lake is None:
        res.unrecognized.append({"code": "lake_unavailable", "detail": "`lake` não encontrado no PATH"})
        return res

    # 1. build do alvo no ambiente fixado
    t0 = time.monotonic()
    try:
        b = subprocess.run([lake, "build", res.module], cwd=root, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=remaining())
    except subprocess.TimeoutExpired:
        res.build = {"status": "timeout", "duration_s": round(time.monotonic() - t0, 3)}
        return res
    log = b.stdout + b.stderr
    res.build = {"status": "success" if b.returncode == 0 else "failure",
                 "duration_s": round(time.monotonic() - t0, 3)}
    if b.returncode != 0:
        res.build["cycle_detected"] = "build cycle detected" in log
        res.build["log_tail"] = log[-4000:]
        return res

    # 2. inspetor
    try:
        insp = ensure_inspector(res.toolchain, lake)
    except InspectorBuildError as e:
        res.unrecognized.append({"code": "inspector_build_failed", "detail": str(e)[-2000:]})
        return res
    res.inspector = {k: v for k, v in insp.items() if k != "path"}
    with tempfile.TemporaryDirectory(prefix="auditor_inspect_") as tmp:
        out = Path(tmp) / "facts.json"
        try:
            p = subprocess.run([lake, "env", insp["path"], res.module, str(out)], cwd=root,
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=remaining())
        except subprocess.TimeoutExpired:
            res.unrecognized.append({"code": "timeout", "detail": "inspetor excedeu o tempo"})
            return res
        if p.returncode != 0 or not out.is_file():
            res.unrecognized.append({"code": "inspector_failed",
                                     "detail": f"exit {p.returncode}: {(p.stdout + p.stderr)[-2000:]}"})
            return res
        try:
            facts = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            res.unrecognized.append({"code": "inspector_output_invalid", "detail": str(e)})
            return res

    _ingest(res, facts, expected)
    _apply_boundary(res, facts, root)
    return res


def _sysroot(root: Path) -> Path | None:
    """Sysroot resolvido pelo elan a partir do `lean-toolchain` do projeto, independente do inspetor."""
    lean = shutil.which("lean")
    if lean is None:
        return None
    p = subprocess.run([lean, "--print-prefix"], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return Path(p.stdout.strip()) if p.returncode == 0 and p.stdout.strip() else None


def _apply_boundary(res: StageBResult, facts: dict, root: Path) -> None:
    """Q7: classifica cada constante com `@[implemented_by]`/`@[extern]` como tcb/user.
    A decisão usa o manifest e as raízes declaradas pelo toolchain (tcb_boundary.py)."""
    sysroot = _sysroot(root)
    if sysroot is None or os.path.normcase(os.path.realpath(sysroot)) !=             os.path.normcase(os.path.realpath(facts.get("sysroot") or "")):
        res.unrecognized.append({"code": "sysroot_mismatch",
                                 "detail": f"elan: {sysroot}; inspetor: {facts.get('sysroot')}"})
        return
    apply_boundary(res, facts, root, sysroot)


def apply_boundary(res: StageBResult, facts: dict, root: Path, sysroot: Path) -> None:
    try:
        b = tb.load_boundary(root, sysroot)
    except tb.BoundaryError as e:
        res.unrecognized.append({"code": "tcb_boundary_undeclared", "detail": str(e)})
        return
    res.boundary = {"toolchain_lib": str(b.toolchain_lib), "toolchain_roots": sorted(b.toolchain_roots),
                    "user_roots": [str(u) for u in b.user_roots], "packages": list(b.packages)}
    extra = tb.unrecognized_search_path(b, facts.get("search_path") or [])
    if extra:
        res.unrecognized.append({"code": "search_path_unrecognized", "detail": extra})
    for d in res.declarations:
        for key in ("implemented_by", "extern"):
            for e in d[key]:
                e["level"], e["level_reason"] = tb.classify(b, e.get("module") or "", e.get("olean"))
                if e["level"] == tb.UNRESOLVED:
                    res.anomalies.append({"declaration": d["name"], "code": "tcb_boundary_unresolved",
                                          "detail": {"attribute": key, "constant": e["name"],
                                                     "module": e.get("module"), "reason": e["level_reason"]}})


def _ingest(res: StageBResult, facts: dict, expected_version: str) -> None:
    if facts.get("inspector_version") != INSPECTOR_VERSION:
        res.unrecognized.append({"code": "inspector_version_mismatch",
                                 "detail": f"{facts.get('inspector_version')!r} ≠ {INSPECTOR_VERSION!r}"})
    if facts.get("lean_version") != expected_version:
        res.unrecognized.append({"code": "toolchain_mismatch",
                                 "detail": f"inspetor rodou com Lean {facts.get('lean_version')!r}, "
                                           f"lean-toolchain fixa {expected_version!r}"})
    if facts.get("module") != res.module:
        res.unrecognized.append({"code": "module_mismatch", "detail": facts.get("module")})
    res.inspector = {**(res.inspector or {}), "lean_version": facts.get("lean_version"),
                     "lean_githash": facts.get("lean_githash")}

    for d in facts.get("declarations", []):
        name = d["name"]
        if sorted(d["axioms_official"]) != sorted(d["axioms_closure"]):
            res.anomalies.append({"declaration": name, "code": "inspector_disagreement",
                                  "detail": {"official": d["axioms_official"], "closure": d["axioms_closure"]}})
        if not isinstance(d.get("native_auxiliary"), list):
            res.anomalies.append({"declaration": name, "code": "inspector_field_missing",
                                  "detail": {"field": "native_auxiliary"}})
            d["native_auxiliary"] = []
        if d["missing"]:
            res.anomalies.append({"declaration": name, "code": "missing_constants",
                                  "detail": {"constants": d["missing"]}})
        for ref in d["axiom_referrers"]:
            for r in ref["referrers"]:
                if r["owner"] is None:
                    res.anomalies.append({"declaration": name, "code": "owner_unresolved",
                                          "detail": {"axiom": ref["axiom"], "referrer": r["name"]}})
        res.declarations.append(d)
    res.owners = {o["name"]: {"docstring": o.get("docstring"), "module": o.get("module")}
                  for o in facts.get("owners", [])}

    md = facts.get("metadata") or {}
    res.metadata = {}
    for k in ("simp", "ext", "reducible", "implemented_by"):
        names = md.get(k)
        if not isinstance(names, list):
            res.unrecognized.append({"code": "metadata_missing", "detail": k})
            continue
        res.metadata[k] = {"count": len(names), "sha256": "sha256:" + hashlib.sha256(
            "\n".join(names).encode("utf-8")).hexdigest()}
