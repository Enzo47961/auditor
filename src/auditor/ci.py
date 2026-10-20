"""Integração CI (componente 7): lógica testável por trás dos workflows do GitHub.

Subcomandos:
  run             audita os arquivos `.lean` de um PR dentro do orçamento (5 min por padrão)
                  e grava relatórios, `outcome.json` e `summary.md` (Job Summary);
  label-decision  decide, a partir do `outcome.json` e da conclusão do job, se o PR recebe o
                  label `auditor-failed-infra` (workflow confiável, sem código do PR);
  comment         monta o comentário pedido por humano (`@auditor report`).

Semântica (spec, componente 7; D-22):
  * orçamento esgotado, timeout ou falha de infraestrutura em qualquer arquivo
    → `infra_failed`: label `auditor-failed-infra`, NÃO bloqueia merge, exige revisão humana;
  * algum arquivo com exit 1 (rejeição ou não resolução) → `audit_failed`: o job falha;
  * `run` sai com 1 só por `audit_failed`; infraestrutura sozinha sai com 0 (não bloqueia).
Nada daqui comenta no PR por iniciativa própria.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OUTCOME_SCHEMA = "auditor-ci-outcome/1"
LABEL = "auditor-failed-infra"
DEFAULT_BUDGET_S = 300.0
MIN_SLICE_S = 5.0          # menos que isso não dá para auditar nada: conta como orçamento esgotado
COMMENT_LIMIT = 60000      # limite do GitHub é 65536 caracteres


def _inspector_cached(target: Path) -> bool | None:
    """O binário do inspetor para o toolchain do projeto já está em cache? (D-7: medir hit rate.)"""
    from auditor.tier1 import stage_b
    root = stage_b.find_project(target)
    if root is None:
        return None
    toolchain = (root / "lean-toolchain").read_text(encoding="utf-8").strip()
    _, key = stage_b.inspector_identity(toolchain)
    exe = stage_b._cache_root() / "inspector" / key / ".lake" / "build" / "bin" / \
        ("inspect.exe" if os.name == "nt" else "inspect")
    return exe.is_file()


def _child_env() -> dict:
    """O subprocesso audita com o MESMO pacote `auditor` que está orquestrando (instalado ou não)."""
    pkg_parent = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = pkg_parent + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def audit_files(files: list[str], policy: str, out_dir: Path, budget_s: float,
                allow_empty: bool = False) -> dict:
    started = time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    results, deleted = [], []
    for i, f in enumerate(files):
        p = Path(f)
        if p.suffix != ".lean":
            continue
        if not p.is_file():
            deleted.append(f)          # removido no PR: nada a auditar
            continue
        remaining = budget_s - (time.monotonic() - started)
        entry = {"file": f, "report": None, "exit_code": None, "status": None,
                 "duration_s": 0.0, "inspector_cache": None, "counts": {}}
        if remaining < MIN_SLICE_S:
            entry["status"] = "skipped_budget"
            results.append(entry)
            continue
        entry["inspector_cache"] = {True: "hit", False: "miss", None: None}[_inspector_cached(p)]
        report = out_dir / f"report-{i:04d}.json"
        cmd = [sys.executable, "-m", "auditor", "check", f, "--output", str(report), "--policy", policy,
               "--timeout", f"{remaining:.1f}"] + (["--allow-empty"] if allow_empty else [])
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=remaining + 30, env=_child_env())
            entry["exit_code"] = proc.returncode
        except subprocess.TimeoutExpired:
            entry["exit_code"] = None
            entry["status"] = "killed_timeout"
        entry["duration_s"] = round(time.monotonic() - t0, 3)
        if report.is_file():
            entry["report"] = report.name
            try:
                r = json.loads(report.read_text(encoding="utf-8"))
                for d in r.get("declarations", []):
                    entry["counts"][d["overall_status"]] = entry["counts"].get(d["overall_status"], 0) + 1
                entry["infra_reasons"] = [x.get("code") for x in r.get("infrastructure", {}).get("reasons", [])]
            except (json.JSONDecodeError, KeyError, TypeError):
                entry["exit_code"] = 2
                entry["infra_reasons"] = ["report_unreadable"]
        if entry["status"] is None:
            entry["status"] = {0: "pass", 1: "fail", 2: "infra"}.get(entry["exit_code"], "infra")
        results.append(entry)

    infra = [r for r in results if r["status"] in ("infra", "skipped_budget", "killed_timeout")]
    failed = [r for r in results if r["status"] == "fail"]
    cache = [r["inspector_cache"] for r in results if r["inspector_cache"]]
    return {
        "schema": OUTCOME_SCHEMA,
        "budget_s": budget_s,
        "elapsed_s": round(time.monotonic() - started, 3),
        "infra_failed": bool(infra),
        "audit_failed": bool(failed),
        "files": results,
        "deleted_files": deleted,
        "inspector_cache": {"hits": cache.count("hit"), "misses": cache.count("miss")},
    }


def summary_markdown(outcome: dict) -> str:
    lines = ["## auditor Tier1 (Fase 0)", ""]
    lines.append("> Correspondência entre enunciado formal e informal: **Não Auditada**. "
                 "Este resultado não significa \"a prova está correta\"; ver o README do auditor.")
    lines.append("")
    if outcome["infra_failed"]:
        lines += [f"**⚠ `{LABEL}`**: a auditoria não concluiu dentro do orçamento ou teve falha de "
                  "infraestrutura. **Não bloqueia o merge, mas exige revisão humana explícita.** "
                  "Timeout nunca é tratado como sucesso.", ""]
    if not outcome["files"]:
        lines.append("Nenhum arquivo `.lean` existente a auditar neste PR.")
    else:
        lines += ["| Arquivo | Resultado | verified | rejected | unresolved | Tempo (s) | Cache do inspetor |",
                  "|---|---|---|---|---|---|---|"]
        for r in outcome["files"]:
            c = r.get("counts", {})
            lines.append(f"| `{r['file']}` | {r['status']} | {c.get('verified', 0)} | {c.get('rejected', 0)} | "
                         f"{c.get('unresolved', 0)} | {r['duration_s']} | {r.get('inspector_cache') or '—'} |")
    lines += ["", f"Orçamento: {outcome['budget_s']} s · usado: {outcome['elapsed_s']} s · "
              f"cache do inspetor: {outcome['inspector_cache']['hits']} hit / "
              f"{outcome['inspector_cache']['misses']} miss",
              "", "Relatórios JSON completos: artefato `auditor-report` desta execução."]
    if outcome["deleted_files"]:
        lines += ["", "Arquivos removidos no PR (não auditados): " +
                  ", ".join(f"`{f}`" for f in outcome["deleted_files"])]
    return "\n".join(lines) + "\n"


def label_decision(outcome_path: Path | None, conclusion: str) -> tuple[bool, str]:
    """Fail-closed: qualquer coisa diferente de um outcome válido sem infra_failed → label.

    O `outcome.json` vem de um job que rodou código do PR: é tratado como dado não confiável.
    Só o campo booleano `infra_failed` é lido, com checagem estrita de tipo."""
    if conclusion not in ("success", "failure"):
        return True, f"job concluído como {conclusion!r}"
    if outcome_path is None or not outcome_path.is_file():
        return True, "outcome ausente"
    try:
        data = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return True, "outcome ilegível"
    if not isinstance(data, dict) or data.get("schema") != OUTCOME_SCHEMA \
            or not isinstance(data.get("infra_failed"), bool):
        return True, "outcome fora do formato"
    if data["infra_failed"]:
        return True, "infra_failed"
    return False, "ok"


def comment_body(summary: str, head_sha: str) -> str:
    head = f"Pedido por um humano (`@auditor report`). Commit `{head_sha[:12]}`.\n\n"
    body = head + summary
    if len(body) > COMMENT_LIMIT:
        body = body[:COMMENT_LIMIT] + "\n\n… (truncado; ver o artefato `auditor-report`)\n"
    return body


def _write_output(path: str | None, **kv) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        for k, v in kv.items():
            fh.write(f"{k}={str(v).lower() if isinstance(v, bool) else v}\n")


def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="auditor-ci")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("files", nargs="*")
    r.add_argument("--files-from", help="arquivo com um caminho por linha")
    r.add_argument("--policy", required=True)
    r.add_argument("--out-dir", required=True)
    r.add_argument("--budget", type=float, default=DEFAULT_BUDGET_S)
    r.add_argument("--allow-empty", action="store_true")
    r.add_argument("--summary", help="onde gravar o markdown (ex.: $GITHUB_STEP_SUMMARY)")
    r.add_argument("--github-output", help="$GITHUB_OUTPUT")
    ld = sub.add_parser("label-decision")
    ld.add_argument("--outcome")
    ld.add_argument("--conclusion", required=True)
    ld.add_argument("--github-output")
    cm = sub.add_parser("comment")
    cm.add_argument("--summary", required=True)
    cm.add_argument("--head-sha", required=True)
    cm.add_argument("--output", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "run":
        files = list(a.files)
        if a.files_from:
            files += [ln.strip() for ln in Path(a.files_from).read_text(encoding="utf-8").splitlines() if ln.strip()]
        out = Path(a.out_dir)
        outcome = audit_files(files, a.policy, out, a.budget, a.allow_empty)
        (out / "outcome.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md = summary_markdown(outcome)
        (out / "summary.md").write_text(md, encoding="utf-8")
        if a.summary:
            with open(a.summary, "a", encoding="utf-8") as fh:
                fh.write(md)
        _write_output(a.github_output, infra_failed=outcome["infra_failed"], audit_failed=outcome["audit_failed"])
        sys.stdout.write(md)
        return 1 if outcome["audit_failed"] else 0
    if a.cmd == "label-decision":
        label, why = label_decision(Path(a.outcome) if a.outcome else None, a.conclusion)
        _write_output(a.github_output, label=label)
        print(f"label={str(label).lower()} ({why})")
        return 0
    body = comment_body(Path(a.summary).read_text(encoding="utf-8"), a.head_sha)
    Path(a.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
