"""Benchmark da Fase 1 (sub-fase 1b): executa e mede, por categoria. `docs/benchmark.md`.

Uso (no fork de medição, depois de `lake exe cache get` e de copiar `benchmark/lean/` para
`<projeto>/Mathlib/AuditorBenchmark/`; workflow `auditor-benchmark`):
    python tools/phase1/benchmark.py run <projeto> --manifest benchmark/manifest.json --policy policy.toml --out out/
    python tools/phase1/benchmark.py report out/ --json bench.json --md bench.md

`run` audita, com o auditor real (`python -m auditor check`), cada arquivo citado pelo manifesto —
casos, controles de validade e ground truths — uma vez por arquivo, e guarda o estado da declaração
de cada caso. `report` calcula, por categoria (nunca agregado):
  * validade: um caso negativo só conta se o ground truth (prova da negação) saiu `verified` e, para
    enunciado trocado, se o controle (enunciado original com a mesma prova) saiu `verified`;
  * sensibilidade: casos negativos válidos que NÃO saíram `verified`;
  * razão certa: o alerta traz um dos códigos esperados;
  * falsos positivos: casos positivos (provas corretas) que não saíram `verified`;
  * precisão: alertas em casos negativos / alertas totais (negativos + positivos).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

POSITIVE = ("correct_hard", "swap_control")
NEGATIVE = ("swapped_statement", "sorry_axiom")


def module_path(project: Path, module: str) -> Path:
    return project / (module.replace(".", "/") + ".lean")


def codes_of(decl: dict | None, report: dict | None) -> set[str]:
    out: set[str] = set()
    if decl:
        for key in ("proof_status", "premises_status"):
            for r in decl[key]["reasons"]:
                out.add(r["code"])
                for it in (r.get("detail") or {}).get("items", []) or []:
                    if isinstance(it, dict) and "code" in it:
                        out.add(it["code"])
        out |= {v["rule"] for v in decl.get("policy_violations", [])}
    if report:
        out |= {u.get("code") for u in (report.get("file_findings") or {}).get("unrecognized", [])
                if isinstance(u, dict)}
    return out


def audit(project: Path, module: str, policy: Path, out: Path, timeout: float) -> dict:
    f = module_path(project, module)
    rep = out / "reports" / (module + ".json")
    rep.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    p = subprocess.run([sys.executable, "-m", "auditor", "check", str(f), "--output", str(rep),
                        "--policy", str(policy), "--timeout-file", str(timeout)],
                       cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout + 120)
    res = {"module": module, "exit_code": p.returncode, "duration_s": round(time.monotonic() - t0, 1),
           "report": rep.name if rep.is_file() else None, "stderr_tail": p.stderr[-1500:]}
    try:   # o relatório não guarda o log de compilação: para diagnóstico, o erro do Lean vai à parte
        if json.loads(rep.read_text(encoding="utf-8"))["compilation"].get("status") == "failure":
            b = subprocess.run(["lake", "build", module], cwd=project, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout)
            log = out / "buildlogs" / (module + ".log")
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_bytes((b.stdout + b.stderr)[-8000:].encode("utf-8"))
            res["build_log"] = log.name
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        pass
    return res


def decl_result(out: Path, module: str, name: str) -> dict:
    rep = out / "reports" / (module + ".json")
    if not rep.is_file():
        return {"found": False, "overall": None, "codes": [], "note": "sem relatório"}
    r = json.loads(rep.read_text(encoding="utf-8"))
    # declaração privada (inclusive privada pelo sistema de módulos): `_private.<Módulo>.0.<nome>`
    d = next((x for x in r["declarations"] if x["declaration_name"] == name
              or x["declaration_name"].split(".0.", 1)[-1] == name and x["declaration_name"].startswith("_private.")),
             None)
    return {"found": d is not None, "overall": d["overall_status"] if d else None,
            "proof": d["proof_status"]["value"] if d else None,
            "codes": sorted(c for c in codes_of(d, r) if c), "exit_code": r.get("exit_code")}


def run(project: Path, manifest: dict, policy: Path, out: Path, timeout: float) -> dict:
    modules = []
    for c in manifest["cases"]:
        modules.append(c["module"])
        gt = c.get("ground_truth") or {}
        if gt.get("module"):
            modules.append(gt["module"])
    audits = {}
    for m in dict.fromkeys(modules):
        audits[m] = audit(project, m, policy, out, timeout)
        print(f"{audits[m]['exit_code']}  {audits[m]['duration_s']:>6} s  {m}", flush=True)
    results = []
    for c in manifest["cases"]:
        res = {"id": c["id"], "category": c["category"], **decl_result(out, c["module"], c["declaration"])}
        gt = c.get("ground_truth") or {}
        if gt.get("module"):
            g = decl_result(out, gt["module"], gt["declaration"])
            res["ground_truth"] = {"verified": g["overall"] == "verified", "overall": g["overall"]}
        results.append(res)
    data = {"manifest": {k: v for k, v in manifest.items() if k != "cases"}, "audits": audits, "results": results,
            "auditor_ref": os.environ.get("AUDITOR_REF")}
    (out / "results.json").write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    return data


def report(data: dict, manifest: dict) -> dict:
    cases = {c["id"]: c for c in manifest["cases"]}
    res = {r["id"]: r for r in data["results"]}
    control = {cases[i]["controls"]: res[i]["overall"] == "verified"
               for i in res if cases[i]["category"] == "swap_control"}
    by_cat: dict[str, dict] = defaultdict(lambda: {"cases": 0, "valid": 0, "invalid": [], "verified": 0,
                                                   "alert": 0, "reason_ok": 0, "misses": [], "alerts_on": []})
    for i, r in res.items():
        c, s = cases[i], by_cat[cases[i]["category"]]
        s["cases"] += 1
        valid = r.get("found", False)
        if "ground_truth" in r and not r["ground_truth"]["verified"]:
            valid = False
        if c["category"] == "swapped_statement" and not control.get(i, False):
            valid = False
        if not valid:
            s["invalid"].append({"id": i, "found": r.get("found"), "ground_truth": r.get("ground_truth"),
                                 "control_verified": control.get(i)})
            continue
        s["valid"] += 1
        if r["overall"] == "verified":
            s["verified"] += 1
            if c["category"] in NEGATIVE:
                s["misses"].append(i)          # falso negativo: catastrófico
        else:
            s["alert"] += 1
            exp = set(c["expected"].get("reasons_any", []))
            if not exp or exp & set(r["codes"]):
                s["reason_ok"] += 1
            if c["category"] in POSITIVE:
                s["alerts_on"].append({"id": i, "declaration": c["declaration"], "codes": r["codes"]})
    out = {}
    for cat, s in sorted(by_cat.items()):
        v = s["valid"] or None
        m = {**s, "verified_rate": round(s["verified"] / v, 4) if v else None,
             "alert_rate": round(s["alert"] / v, 4) if v else None}
        if cat in NEGATIVE:
            m["sensitivity"] = m["alert_rate"]
            m["false_negatives"] = len(s["misses"])
        if cat in POSITIVE:
            m["false_positive_rate"] = m["alert_rate"]
        out[cat] = m
    neg_alerts = sum(out[c]["alert"] for c in NEGATIVE if c in out)
    pos_alerts = sum(out[c]["alert"] for c in POSITIVE if c in out)
    total = neg_alerts + pos_alerts
    return {"by_category": out, "precision": round(neg_alerts / total, 4) if total else None,
            "alerts_on_negatives": neg_alerts, "alerts_on_positives": pos_alerts}


def to_md(r: dict) -> str:
    lines = ["| categoria | casos | válidos | verified | alerta | razão certa | FN | taxa |", "|---|---|---|---|---|---|---|---|"]
    for cat, m in r["by_category"].items():
        rate = m.get("sensitivity", m.get("false_positive_rate", m["alert_rate"]))
        lines.append(f"| {cat} | {m['cases']} | {m['valid']} | {m['verified']} | {m['alert']} | {m['reason_ok']} | "
                     f"{m.get('false_negatives', '—')} | {rate} |")
    lines += ["", f"Precisão dos alertas (negativos / total): {r['precision']} "
                  f"({r['alerts_on_negatives']} em negativos, {r['alerts_on_positives']} em positivos)."]
    for cat, m in r["by_category"].items():
        if m["invalid"]:
            lines.append(f"- {cat}, inválidos: " + ", ".join(x["id"] for x in m["invalid"]))
        if m["alerts_on"]:
            lines.append(f"- {cat}, alertas em provas corretas: " +
                         "; ".join(f"{x['id']} {x['declaration']} ({', '.join(x['codes'])})" for x in m["alerts_on"]))
        if m["misses"]:
            lines.append(f"- **{cat}, FALSO NEGATIVO:** " + ", ".join(m["misses"]))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("project", type=Path)
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--policy", type=Path, required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--timeout-file", type=float, default=600.0)
    p = sub.add_parser("report")
    p.add_argument("out", type=Path)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--json", type=Path)
    p.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
    if a.cmd == "run":
        a.out.mkdir(parents=True, exist_ok=True)
        run(a.project.resolve(), manifest, a.policy.resolve(), a.out.resolve(), a.timeout_file)
        return 0
    data = json.loads((a.out / "results.json").read_text(encoding="utf-8"))
    rep = report(data, manifest)
    if a.json:
        a.json.write_bytes((json.dumps(rep, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    md = to_md(rep)
    if a.md:
        a.md.write_bytes(md.encode("utf-8"))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
