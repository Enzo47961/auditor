"""Exclusão (B) dos PRs do estudo de usuário, pelo relatório do auditor (Fase 1, 1c; docs/user-study.md).

Uso (no repositório de medições, sobre o Mathlib em `e1b2403b` com `lake exe cache get` feito):
    python tools/phase1/study_audit.py <projeto> --selection study/selection.json --patches study/patches \\
        --policy policy.toml --out out/

Para cada PR elegível de `study/selection.json` (saída de `study_select.py`): aplica o patch sobre a
base, audita cada arquivo alterado como o `auditor-ci` faria (`auditor check … --changed <outros>`),
guarda os relatórios e desfaz o patch. Depois decide a exclusão da opção (B) (instrução 26):
  * `ctorIdx`: alguma declaração com `implemented_by_candidate` cujas constantes incluem `….ctorIdx`;
  * `backward.*`: alguma razão `set_option_unrecognized`/`set_option_unattributed` cuja opção começa
    por `backward.` (a opção sai do achado `set_option` da Etapa A, pela linha).
A lista de excluídos, com o motivo, é parte do resultado publicado.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def audit_pr(project: Path, row: dict, patches: Path, policy: Path, out: Path) -> dict:
    patch = patches / row["patch"]
    subprocess.run(["git", "-C", str(project), "apply", str(patch)], check=True)
    reports = {}
    try:
        for f in row["files"]:
            rep = out / "reports" / str(row["pr"]) / (f.replace("/", ".") + ".json")
            rep.parent.mkdir(parents=True, exist_ok=True)
            others = [a for g in row["files"] if g != f for a in ("--changed", str(project / g))]
            p = subprocess.run([sys.executable, "-m", "auditor", "check", str(project / f), "--output", str(rep),
                                "--policy", str(policy), "--timeout-file", "600", *others],
                               cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
            reports[f] = {"exit_code": p.returncode, "report": str(rep.relative_to(out)) if rep.is_file() else None}
    finally:
        subprocess.run(["git", "-C", str(project), "apply", "-R", str(patch)], check=True)
    return reports


def exclusion(out: Path, reports: dict) -> tuple[list[str], dict]:
    causes, counts = set(), {"declarations": 0, "verified": 0}
    for f, r in reports.items():
        if not r["report"]:
            causes.add(f"sem relatório ({f})")
            continue
        rep = json.loads((out / r["report"]).read_text(encoding="utf-8"))
        opt_by_line = {x["line"]: x.get("option") or "" for x in rep["file_findings"]["stage_a_candidates"]
                       if x["code"] == "set_option"}
        for d in rep["declarations"]:
            counts["declarations"] += 1
            counts["verified"] += d["overall_status"] == "verified"
            for x in d["proof_status"]["reasons"]:
                det = x.get("detail") or {}
                if x["code"] == "implemented_by_candidate" and any(
                        str(c).endswith(".ctorIdx") for c in det.get("constants", [])):
                    causes.add("ctorIdx")
                if x["code"] in ("set_option_unrecognized", "set_option_unattributed"):
                    opt = det.get("option") or opt_by_line.get(det.get("line"), "")
                    if str(opt).startswith("backward."):
                        causes.add("backward.*")
    return sorted(causes), counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sel = json.loads(a.selection.read_text(encoding="utf-8"))
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in sel["commits"]:
        if not row["eligible"]:
            continue
        reports = audit_pr(a.project.resolve(), row, a.patches.resolve(), a.policy.resolve(), out)
        causes, counts = exclusion(out, reports)
        rows.append({"pr": row["pr"], "sha": row["sha"], "author": row.get("author"), "stratum": row["stratum"],
                     "files": row["files"], "excluded": bool(causes), "exclusion_causes": causes, **counts,
                     "reports": reports})
        print(f"#{row['pr']}  {row['stratum']:<11} {'EXCLUÍDO ' + ', '.join(causes) if causes else 'mantido':<30} "
              f"{counts['verified']}/{counts['declarations']} verified", flush=True)
    data = {"base": sel["base"], "rule": "exclusão (B): ctorIdx gerado ou backward.* (instrução 26)", "prs": rows,
            "kept": {s: [r["pr"] for r in rows if not r["excluded"] and r["stratum"] == s]
                     for s in ("success", "fail_closed")},
            "excluded": [{"pr": r["pr"], "causes": r["exclusion_causes"]} for r in rows if r["excluded"]]}
    (out / "study-audit.json").write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(json.dumps({"kept": data["kept"], "excluded": data["excluded"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
