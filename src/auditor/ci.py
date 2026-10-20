"""Integração CI (componente 7): lógica testável por trás dos workflows do GitHub.

Subcomandos:
  run             audita os arquivos `.lean` de um PR dentro do orçamento e grava relatórios,
                  `outcome.json` e `summary.md` (Job Summary);
  label-decision  decide, a partir do `outcome.json` e da conclusão do job, qual label o PR
                  recebe (workflow confiável, sem código do PR);
  comment         monta o comentário pedido por humano (`@auditor report`).

Orçamento e timeouts (instrução 11: D-21, D-28):
  * o orçamento é wall-clock do PR, do trigger até o relatório, e inclui a preparação
    (`lake exe cache get`); `--started-at` dá a origem do relógio;
  * 5 min valem para o steady-state (cache `warm` ou `delta`). Com cache `cold` (primeiro run
    num fork, cache despejado), o orçamento é o estendido (`--first-run-budget`, 15 min) e o
    resultado declara `first_run: true`; se passar dos 5 min sem estourar o estendido, não é
    falha: `cache_cold_extension` e label `auditor-first-run`;
  * cada arquivo tem timeout próprio (`--timeout-file`, 90 s). Arquivo que estoura o timeout
    encerra a auditoria do PR: os demais não são auditados e o PR sai com exit 2.

Exit codes de `run` (os da CLI, no nível do PR): 0 tudo verificado; 1 rejeição ou não
resolução sem falha de infraestrutura; 2 infraestrutura (orçamento, timeout, exit 2 de algum
arquivo). O workflow falha o job só por `audit_failed` (D-22); infraestrutura → label
`auditor-failed-infra`, não bloqueia merge. Nada daqui comenta no PR por iniciativa própria.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

OUTCOME_SCHEMA = "auditor-ci-outcome/2"
LABEL = "auditor-failed-infra"
LABEL_FIRST_RUN = "auditor-first-run"
DEFAULT_BUDGET_S = 300.0             # spec: 5 min, steady-state
DEFAULT_FIRST_RUN_BUDGET_S = 900.0   # cache cold (instrução 11, D-28)
DEFAULT_TIMEOUT_FILE_S = 90.0        # instrução 11, D-21; reajustar pelo p95 medido na camada 2
MIN_SLICE_S = 5.0          # menos que isso não dá para auditar nada: conta como orçamento esgotado
KILL_GRACE_S = 30.0        # folga para o subprocesso gravar o relatório de timeout
COMMENT_LIMIT = 60000      # limite do GitHub é 65536 caracteres
BUILD_CACHE = ("hit", "partial", "miss", "none")
CLOCK_KINDS = ("trigger", "job_start")
INFRA_STATUSES = ("infra", "timeout", "skipped_budget", "not_audited_after_timeout")


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


def _prebuild_inspector(target: Path) -> None:
    """Compila o inspetor antes do primeiro arquivo, para que a compilação conte no orçamento
    do PR e não no timeout por arquivo. Falha aqui não é decidida aqui: o arquivo a reporta."""
    from auditor.tier1 import stage_b
    root, lake = stage_b.find_project(target), shutil.which("lake")
    if root is None or lake is None:
        return
    try:
        stage_b.ensure_inspector((root / "lean-toolchain").read_text(encoding="utf-8").strip(), lake)
    except (stage_b.InspectorBuildError, OSError):
        pass


def cache_state(build_cache: str, inspector_cached: bool | None) -> str:
    """`cold` só com evidência positiva de cache frio: o orçamento estendido nunca é concedido
    por dúvida. Sinal ausente (`none`, `None`) não conta como frio."""
    if build_cache == "miss" or inspector_cached is False:
        return "cold"
    if build_cache == "partial":
        return "delta"
    return "warm"


def _child_env() -> dict:
    """O subprocesso audita com o MESMO pacote `auditor` que está orquestrando (instalado ou não)."""
    pkg_parent = str(Path(__file__).resolve().parent.parent)
    env = dict(os.environ)
    env["PYTHONPATH"] = pkg_parent + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return env


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def audit_files(files: list[str], policy: str, out_dir: Path, budget_s: float = DEFAULT_BUDGET_S,
                allow_empty: bool = False, timeout_file_s: float = DEFAULT_TIMEOUT_FILE_S,
                first_run_budget_s: float = DEFAULT_FIRST_RUN_BUDGET_S, build_cache: str = "none",
                setup_elapsed_s: float = 0.0, clock_origin: str = "auditor_start") -> dict:
    started = time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = [f for f in files if Path(f).suffix == ".lean" and Path(f).is_file()]
    deleted = [f for f in files if Path(f).suffix == ".lean" and not Path(f).is_file()]

    inspector = _inspector_cached(Path(existing[0])) if existing else None
    state = cache_state(build_cache, inspector)
    first_run = state == "cold"
    effective = first_run_budget_s if first_run else budget_s
    deadline = started + effective - setup_elapsed_s
    if existing and inspector is False and deadline - time.monotonic() >= MIN_SLICE_S:
        _prebuild_inspector(Path(existing[0]))

    results, aborted = [], False
    for i, f in enumerate(existing):
        entry = {"file": f, "report": None, "exit_code": None, "status": None,
                 "duration_s": 0.0, "timeout_s": None, "inspector_cache": None, "counts": {}}
        remaining = deadline - time.monotonic()
        if aborted:
            entry["status"] = "not_audited_after_timeout"
            results.append(entry)
            continue
        if remaining < MIN_SLICE_S:
            entry["status"] = "skipped_budget"
            results.append(entry)
            continue
        entry["inspector_cache"] = {True: "hit", False: "miss", None: None}[_inspector_cached(Path(f))]
        limit = min(timeout_file_s, remaining)
        entry["timeout_s"] = round(limit, 1)
        report = out_dir / f"report-{i:04d}.json"
        cmd = [sys.executable, "-m", "auditor", "check", f, "--output", str(report), "--policy", policy,
               "--timeout-file", f"{limit:.1f}"] + (["--allow-empty"] if allow_empty else [])
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                  timeout=limit + KILL_GRACE_S, env=_child_env())
            entry["exit_code"] = proc.returncode
        except subprocess.TimeoutExpired:
            entry["status"] = "timeout"
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
        if entry["status"] is None and "timeout" in entry.get("infra_reasons", []):
            entry["status"] = "timeout"
        if entry["status"] is None:
            entry["status"] = {0: "pass", 1: "fail", 2: "infra"}.get(entry["exit_code"], "infra")
        if entry["status"] == "timeout":
            entry["timeout_kind"] = "file" if limit >= timeout_file_s else "budget"
            aborted = True
        results.append(entry)

    infra = [r for r in results if r["status"] in INFRA_STATUSES]
    failed = [r for r in results if r["status"] == "fail"]
    cache = [r["inspector_cache"] for r in results if r["inspector_cache"]]
    audit_elapsed = time.monotonic() - started
    elapsed = setup_elapsed_s + audit_elapsed
    return {
        "schema": OUTCOME_SCHEMA,
        "exit_code": 2 if infra else 1 if failed else 0,
        "infra_failed": bool(infra),
        "audit_failed": bool(failed),
        "timeout_aborted": aborted,
        "cache_state": state,
        "cache_signals": {"build_cache": build_cache,
                          "inspector": {True: "hit", False: "miss", None: None}[inspector]},
        "first_run": first_run,
        "cache_cold_extension": first_run and not infra and elapsed > budget_s,
        "budget_s": effective,
        "steady_state_budget_s": budget_s,
        "first_run_budget_s": first_run_budget_s,
        "timeout_file_s": timeout_file_s,
        "clock_origin": clock_origin,
        "setup_elapsed_s": round(setup_elapsed_s, 3),
        "audit_elapsed_s": round(audit_elapsed, 3),
        "elapsed_s": round(elapsed, 3),
        "file_duration_p95_s": _p95([r["duration_s"] for r in results if r["exit_code"] is not None
                                     or r["status"] == "timeout"]),
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
        why = ("um arquivo estourou o timeout por arquivo; os seguintes não foram auditados"
               if outcome["timeout_aborted"] else
               "a auditoria não concluiu dentro do orçamento ou teve falha de infraestrutura")
        lines += [f"**⚠ `{LABEL}`** (exit 2): {why}. **Não bloqueia o merge, mas exige revisão humana "
                  "explícita.** Timeout nunca é tratado como sucesso.", ""]
    if outcome["cache_cold_extension"]:
        lines += [f"**ℹ `{LABEL_FIRST_RUN}`**: cache `cold` (primeiro run); a auditoria passou dos "
                  f"{outcome['steady_state_budget_s']:g} s do steady-state dentro do orçamento estendido "
                  f"({outcome['first_run_budget_s']:g} s). Não é falha; o SLA de 5 min vale para o steady-state.", ""]
    if not outcome["files"]:
        lines.append("Nenhum arquivo `.lean` existente a auditar neste PR.")
    else:
        lines += ["| Arquivo | Resultado | verified | rejected | unresolved | Tempo (s) | Cache do inspetor |",
                  "|---|---|---|---|---|---|---|"]
        for r in outcome["files"]:
            c = r.get("counts", {})
            lines.append(f"| `{r['file']}` | {r['status']} | {c.get('verified', 0)} | {c.get('rejected', 0)} | "
                         f"{c.get('unresolved', 0)} | {r['duration_s']} | {r.get('inspector_cache') or '—'} |")
    p95 = outcome["file_duration_p95_s"]
    lines += ["", f"cache_state: `{outcome['cache_state']}`"
              f"{' (first_run)' if outcome['first_run'] else ''} · orçamento: {outcome['budget_s']:g} s "
              f"(relógio desde `{outcome['clock_origin']}`) · preparação: {outcome['setup_elapsed_s']} s · "
              f"auditoria: {outcome['audit_elapsed_s']} s · total: {outcome['elapsed_s']} s",
              "", f"timeout por arquivo: {outcome['timeout_file_s']:g} s · p95 por arquivo: "
              f"{'—' if p95 is None else p95} s · cache do inspetor: {outcome['inspector_cache']['hits']} hit / "
              f"{outcome['inspector_cache']['misses']} miss",
              "", "Relatórios JSON completos: artefato `auditor-report` desta execução."]
    if outcome["deleted_files"]:
        lines += ["", "Arquivos removidos no PR (não auditados): " +
                  ", ".join(f"`{f}`" for f in outcome["deleted_files"])]
    return "\n".join(lines) + "\n"


def label_decision(outcome_path: Path | None, conclusion: str) -> tuple[str | None, str]:
    """Qual label o PR recebe. Fail-closed: qualquer coisa diferente de um outcome válido → LABEL.

    O `outcome.json` vem de um job que rodou código do PR: é tratado como dado não confiável.
    Só os booleanos `infra_failed` e `cache_cold_extension` são lidos, com checagem estrita."""
    if conclusion not in ("success", "failure"):
        return LABEL, f"job concluído como {conclusion!r}"
    if outcome_path is None or not outcome_path.is_file():
        return LABEL, "outcome ausente"
    try:
        data = json.loads(outcome_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return LABEL, "outcome ilegível"
    if not isinstance(data, dict) or data.get("schema") != OUTCOME_SCHEMA \
            or not isinstance(data.get("infra_failed"), bool) \
            or not isinstance(data.get("cache_cold_extension"), bool):
        return LABEL, "outcome fora do formato"
    if data["infra_failed"]:
        return LABEL, "infra_failed"
    if data["cache_cold_extension"]:
        return LABEL_FIRST_RUN, "cache_cold_extension"
    return None, "ok"


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


def _parse_instant(s: str) -> datetime:
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("instante sem fuso horário")
    return t


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
    r.add_argument("--budget", type=float, default=DEFAULT_BUDGET_S, help="steady-state (s); spec: 300")
    r.add_argument("--first-run-budget", type=float, default=DEFAULT_FIRST_RUN_BUDGET_S,
                   help="orçamento com cache cold (s)")
    r.add_argument("--timeout-file", type=float, default=DEFAULT_TIMEOUT_FILE_S, help="timeout por arquivo (s)")
    r.add_argument("--build-cache", choices=BUILD_CACHE, default="none",
                   help="restauração do cache de build do alvo: hit (chave exata), partial, miss, none")
    r.add_argument("--started-at", help="origem do relógio do PR (ISO 8601 com fuso)")
    r.add_argument("--started-at-kind", choices=CLOCK_KINDS, default="trigger")
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
        setup, origin = 0.0, "auditor_start"
        if a.started_at:
            try:
                setup = max(0.0, (datetime.now(timezone.utc) - _parse_instant(a.started_at)).total_seconds())
                origin = a.started_at_kind
            except ValueError as e:
                sys.stderr.write(f"auditor-ci: --started-at inválido ({e}); relógio desde o início do auditor-ci\n")
                origin = "auditor_start_fallback"
        out = Path(a.out_dir)
        outcome = audit_files(files, a.policy, out, a.budget, a.allow_empty, a.timeout_file,
                              a.first_run_budget, a.build_cache, setup, origin)
        (out / "outcome.json").write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md = summary_markdown(outcome)
        (out / "summary.md").write_text(md, encoding="utf-8")
        if a.summary:
            with open(a.summary, "a", encoding="utf-8") as fh:
                fh.write(md)
        _write_output(a.github_output, exit_code=outcome["exit_code"], infra_failed=outcome["infra_failed"],
                      audit_failed=outcome["audit_failed"], cache_state=outcome["cache_state"])
        sys.stdout.write(md)
        return outcome["exit_code"]
    if a.cmd == "label-decision":
        label, why = label_decision(Path(a.outcome) if a.outcome else None, a.conclusion)
        _write_output(a.github_output, label=label or "")
        print(f"label={label or ''} ({why})")
        return 0
    body = comment_body(Path(a.summary).read_text(encoding="utf-8"), a.head_sha)
    Path(a.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
