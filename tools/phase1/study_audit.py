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


def audit_pr(project: Path, row: dict, patches: Path, policy: Path, out: Path, apply: bool = True) -> dict:
    patch = patches / row["patch"] if apply else None
    if apply:
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
        if apply:
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


STATUS_CODE = {"Rejeitada": "rejected", "Não resolvida": "unresolved"}


def known_cause(code: str, detail: dict, opt_by_line: dict) -> bool:
    """Causas conhecidas da 1c (instruções 26 e 28)."""
    if code == "implemented_by_candidate":
        return any(str(c).endswith(".ctorIdx") for c in detail.get("constants", []))
    if code in ("set_option_unrecognized", "set_option_unattributed"):
        return str(detail.get("option") or opt_by_line.get(detail.get("line"), "")).startswith("backward.")
    return code == "target_defines_executable_code"


def check_defects(project: Path, defects: dict, patches: Path, defdir: Path, policy: Path, out: Path) -> list[dict]:
    """Aplica PR + defeito, audita os arquivos e confere: a declaração esperada sai com o estado e a
    razão esperados, e essa razão não é de causa conhecida."""
    results = []
    for d in defects["defects"]:
        pp, dp = (patches / d["pr_patch"]).resolve(), (defdir / d["defect_patch"]).resolve()
        subprocess.run(["git", "-C", str(project), "apply", str(pp)], check=True)
        try:
            subprocess.run(["git", "-C", str(project), "apply", str(dp)], check=True)
            try:
                row = {"pr": d["pr"], "files": d["files"]}
                reports = audit_pr(project, row | {"patch": None}, patches, policy, out, apply=False)
                for f, r in reports.items():   # o relatório não traz a mensagem do Lean: guardar o log
                    rep = json.loads((out / r["report"]).read_text(encoding="utf-8")) if r["report"] else {}
                    if rep.get("compilation", {}).get("status") != "success":
                        log = out / "reports" / str(d["pr"]) / (f.replace("/", ".") + ".build.log")
                        p = subprocess.run(["lake", "env", "lean", f], cwd=project, capture_output=True,
                                           text=True, encoding="utf-8", errors="replace")
                        log.write_text(p.stdout + p.stderr, encoding="utf-8")
                        r["build_log"] = str(log.relative_to(out))
                        print(f"  {f}: compilação falhou; log em {r['build_log']}\n{(p.stdout + p.stderr)[-3000:]}",
                              flush=True)
            finally:
                subprocess.run(["git", "-C", str(project), "apply", "-R", str(dp)], check=True)
        finally:
            subprocess.run(["git", "-C", str(project), "apply", "-R", str(pp)], check=True)
        decls, opts = {}, {}
        for f, r in reports.items():
            if not r["report"]:
                continue
            rep = json.loads((out / r["report"]).read_text(encoding="utf-8"))
            opts = {x["line"]: x.get("option") or "" for x in rep["file_findings"]["stage_a_candidates"]
                    if x["code"] == "set_option"}
            for dd in rep["declarations"]:
                decls[dd["declaration_name"].split(".0.", 1)[-1]] = (dd, opts)
        checks = []
        for e in d["expect"]:
            dd, o = decls.get(e["declaration"], (None, {}))
            reasons = [(x["code"], x.get("detail") or {}) for x in (dd or {}).get("proof_status", {}).get("reasons", [])]
            hit = [det for c, det in reasons if c == e["reason"] and not known_cause(c, det, o)]
            status = dd["proof_status"]["value"] if dd else None
            checks.append({"declaration": e["declaration"], "found": dd is not None, "status": status,
                           "reasons": [c for c, _ in reasons],
                           "ok": status in (e["status"], STATUS_CODE.get(e["status"])) and bool(hit)})
        results.append({"id": d["id"], "pr": d["pr"], "checks": checks, "ok": all(c["ok"] for c in checks),
                        "reports": reports})
        print(f"defeito {d['id']} (#{d['pr']}): {'OK' if results[-1]['ok'] else 'FALHOU'} {checks}", flush=True)
    return results


def audit_study(project: Path, prs: list[dict], defects: dict, patches: Path, defdir: Path, policy: Path,
                out: Path) -> list[dict]:
    """Os PRs do estudo, como os revisores os veem: PR + defeito plantado (se houver) aplicados."""
    by_pr = {d["pr"]: d for d in defects["defects"]}
    sel = {r["pr"]: r for r in json.loads((patches.parent / "selection.json").read_text(encoding="utf-8"))["commits"]}
    rows = []
    for p in prs:
        pp = (patches / sel[p["pr"]]["patch"]).resolve()
        d = by_pr.get(p["pr"])
        files = list(dict.fromkeys(p["files"] + (d["files"] if d else [])))
        subprocess.run(["git", "-C", str(project), "apply", str(pp)], check=True)
        try:
            if d:
                subprocess.run(["git", "-C", str(project), "apply", str((defdir / d["defect_patch"]).resolve())], check=True)
            try:
                reports = audit_pr(project, {"pr": p["pr"], "files": files, "patch": None}, patches, policy, out, apply=False)
            finally:
                if d:
                    subprocess.run(["git", "-C", str(project), "apply", "-R", str((defdir / d["defect_patch"]).resolve())], check=True)
        finally:
            subprocess.run(["git", "-C", str(project), "apply", "-R", str(pp)], check=True)
        rows.append({"pr": p["pr"], "defect": d["id"] if d else None, "reports": reports})
        print(f"#{p['pr']} {'defeito ' + d['id'] if d else ''} {reports}", flush=True)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--selection", type=Path, required=True)
    ap.add_argument("--patches", type=Path, required=True)
    ap.add_argument("--policy", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--defects", type=Path, help="study/defects.json: verifica os defeitos plantados")
    ap.add_argument("--prs", type=Path, help="study/prs.json: audita os PRs do estudo com os defeitos aplicados (exige --defects)")
    a = ap.parse_args(argv)
    sel = json.loads(a.selection.read_text(encoding="utf-8"))
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if a.prs:
        res = audit_study(a.project.resolve(), json.loads(a.prs.read_text(encoding="utf-8")),
                          json.loads(a.defects.read_text(encoding="utf-8")), a.patches.resolve(),
                          a.defects.resolve().parent / "defects", a.policy.resolve(), out)
        (out / "study-prs.json").write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        return 0
    if a.defects:
        res = check_defects(a.project.resolve(), json.loads(a.defects.read_text(encoding="utf-8")),
                            a.patches.resolve(), a.defects.resolve().parent / "defects", a.policy.resolve(), out)
        (out / "study-defects.json").write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        return 0 if all(r["ok"] for r in res) else 1
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
