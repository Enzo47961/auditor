"""Coleta e relatório do estudo de usuário (Fase 1, 1c; docs/user-study.md, seções 3 e 4).

    python tools/phase1/study_run.py prs      --selection study/selection.json --out study/prs.json
    python tools/phase1/study_run.py assign   --prs study/prs.json --reviewers study/reviewers.json \\
                                              --seed <semente publicada> --out study/assignment.json
    python tools/phase1/study_run.py forms    --assignment study/assignment.json --out study/forms/
    python tools/phase1/study_run.py alerts   --reports <saída do auditor-study>/reports --prs study/prs.json --out study/alerts.json
    python tools/phase1/study_run.py report   --assignment study/assignment.json --forms study/forms/ \\
                                              --alerts study/alerts.json --defects study/defects.json --out study/result.json

* `prs`: os 10 PRs, pela regra mecânica — 5 por estrato, na ordem de integração no Mathlib.
* `assign`: cada PR a 2 revisores diferentes, um COM e outro SEM o auditor; ninguém revisa o próprio
  PR (conflito de interesse, instrução 27); carga e condições equilibradas por revisor; ordem
  aleatória. Tudo derivado SÓ da semente publicada e das entradas, então qualquer um reproduz.
* `forms`: um CSV por revisor, com as revisões na ordem sorteada e as colunas da seção 4.
* `report`: as medidas da seção 4, por PR e por estrato, nunca só agregadas: T_net principal (sem o
  tempo das causas conhecidas) e T_net com elas; taxa de falsos alertas só sobre alertas que não são
  de causa conhecida; os três desfechos de cada defeito plantado, separados.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from datetime import datetime
from pathlib import Path

PER_STRATUM = 5
STRATA = ("success", "fail_closed")
FORM_COLUMNS = ["order", "pr", "condition", "start", "end", "verdict", "problems_found",
                "report_reading_min", "alerts_judged_false", "known_cause_min", "notes"]
VERDICTS = ("integro", "nao_integro", "nao_sei")


def select_prs(selection: dict) -> list[dict]:
    """5 por estrato, na ordem de integração (a ordem de `selection.json` é a de integração)."""
    out = []
    for s in STRATA:
        rows = [r for r in selection["commits"] if r["eligible"] and r["stratum"] == s]
        out += [{"pr": r["pr"], "stratum": s, "author": r.get("author"), "sha": r["sha"], "files": r["files"]}
                for r in rows[:PER_STRATUM]]
    return out


def assign(prs: list[dict], reviewers: list[dict], seed: int, tries: int = 100_000) -> dict:
    """Sorteio com restrições, por rejeição: a primeira tentativa válida do gerador com a semente."""
    rng = random.Random(seed)
    names = [r["id"] for r in reviewers]
    handles = {r["id"]: {h.lower() for h in r.get("github", [])} for r in reviewers}
    total = 2 * len(prs)
    base, extra = divmod(total, len(names))
    for attempt in range(1, tries + 1):
        load = {n: 0 for n in names}
        cond = {n: {"with": 0, "without": 0} for n in names}
        rows, ok = [], True
        for p in prs:
            allowed = [n for n in names if (p.get("author") or "").lower() not in handles[n]]
            if len(allowed) < 2:
                raise ValueError(f"PR #{p['pr']}: menos de 2 revisores sem conflito de interesse")
            pair = rng.sample(allowed, 2)
            for n, c in zip(pair, ("with", "without")):
                load[n] += 1
                cond[n][c] += 1
            rows.append({"pr": p["pr"], "stratum": p["stratum"], "with": pair[0], "without": pair[1]})
        loads = sorted(load.values())
        ok = loads == sorted([base + 1] * extra + [base] * (len(names) - extra)) and all(
            abs(c["with"] - c["without"]) <= 1 for c in cond.values())
        if ok:
            order = {}
            for n in names:
                mine = [(r["pr"], "with" if r["with"] == n else "without") for r in rows if n in (r["with"], r["without"])]
                rng.shuffle(mine)
                order[n] = [{"order": i + 1, "pr": pr, "condition": c} for i, (pr, c) in enumerate(mine)]
            return {"seed": seed, "attempt": attempt, "prs": prs, "reviewers": names, "pairs": rows,
                    "order": order, "load": load, "conditions": cond,
                    "conflicts_excluded": [{"pr": p["pr"], "reviewer": n} for p in prs for n in names
                                           if (p.get("author") or "").lower() in handles[n]]}
    raise ValueError("nenhum sorteio válido; rever as restrições")


def write_forms(assignment: dict, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for n, rows in assignment["order"].items():
        p = out / f"reviewer-{n}.csv"
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, FORM_COLUMNS)
            w.writeheader()
            for r in rows:
                w.writerow({"order": r["order"], "pr": r["pr"], "condition": r["condition"]})
        paths.append(p)
    return paths


def _minutes(a: str, b: str) -> float:
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60


def _num(x: str) -> float:
    return float(x) if str(x).strip() else 0.0


def read_forms(forms: Path) -> list[dict]:
    rows = []
    for p in sorted(forms.glob("reviewer-*.csv")):
        n = p.stem.removeprefix("reviewer-")
        with p.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if not r["start"].strip():
                    continue
                if r["verdict"] not in VERDICTS:
                    raise ValueError(f"{p.name}, PR {r['pr']}: veredito {r['verdict']!r} fora de {VERDICTS}")
                rows.append({"reviewer": n, "pr": int(r["pr"]), "condition": r["condition"],
                             "minutes": _minutes(r["start"], r["end"]), "verdict": r["verdict"],
                             "reading_min": _num(r["report_reading_min"]), "known_min": _num(r["known_cause_min"]),
                             "judged_false": {x.strip() for x in r["alerts_judged_false"].split(";") if x.strip()},
                             "problems": r["problems_found"]})
    return rows


def report(assignment: dict, forms: list[dict], alerts: dict, defects: dict) -> dict:
    """`alerts`: {pr: [{"declaration", "known_cause": bool}]} — os alertas (declarações não `verified`)
    do relatório do auditor, com a causa já atribuída mecanicamente antes de ler os formulários."""
    defect_decls = {(d["pr"], e["declaration"]) for d in defects["defects"] for e in d["expect"]}
    by = {(f["pr"], f["condition"]): f for f in forms}
    per_pr = []
    for p in assignment["prs"]:
        pr = p["pr"]
        conv, assist = by.get((pr, "without")), by.get((pr, "with"))
        al = alerts.get(str(pr), [])
        unknown = [a for a in al if not a["known_cause"]]
        row = {"pr": pr, "stratum": p["stratum"], "complete": bool(conv and assist),
               "alerts": len(al), "known_cause_alerts": len(al) - len(unknown), "other_alerts": len(unknown)}
        if conv and assist:
            row |= {"t_conventional": conv["minutes"], "t_assisted": assist["minutes"],
                    "t_net_with_known": conv["minutes"] - assist["minutes"],
                    "t_net": conv["minutes"] - (assist["minutes"] - assist["known_min"]),
                    "reading_min": assist["reading_min"], "known_cause_min": assist["known_min"]}
            false = [a for a in unknown if (pr, a["declaration"]) not in defect_decls
                     and a["declaration"] in assist["judged_false"]]
            row["false_alerts"] = len(false)
            row["false_alert_rate"] = len(false) / len(unknown) if unknown else None
        per_pr.append(row)

    def summary(rows):
        done = [r for r in rows if r["complete"]]
        rates = [r["false_alert_rate"] for r in done if r["false_alert_rate"] is not None]
        return {"prs": len(rows), "complete": len(done),
                "t_net_median": statistics.median(r["t_net"] for r in done) if done else None,
                "t_net_with_known_median": statistics.median(r["t_net_with_known"] for r in done) if done else None,
                "false_alert_rate_median": statistics.median(rates) if rates else None}

    outcomes = []
    for d in defects["defects"]:
        decls = {e["declaration"] for e in d["expect"]}
        flagged = any(a["declaration"] in decls for a in alerts.get(str(d["pr"]), []))
        for cond in ("with", "without"):
            f = by.get((d["pr"], cond))
            if not f:
                continue
            found = f["verdict"] == "nao_integro"
            o = {"defect": d["id"], "pr": d["pr"], "condition": cond, "reviewer_found": found}
            if cond == "with":   # desfechos da seção 2 (condição 2): só fazem sentido com o relatório à vista
                o["outcome"] = "c" if not flagged else ("a" if found else "b")
            outcomes.append(o)
    s = {k: summary([r for r in per_pr if r["stratum"] == k]) for k in STRATA}
    s["all"] = summary(per_pr)
    return {"seed": assignment["seed"], "per_pr": per_pr, "summary": s, "defects": outcomes,
            "criteria": {"accept": "t_net_median > 0 e false_alert_rate_median < 0.30",
                         "kill": "t_net_median < 0 e false_alert_rate_median > 0.50"}}


def collect_alerts(reports: Path, prs: list[dict]) -> dict:
    """Alertas por PR (declaração não `verified`), com a causa atribuída mecanicamente pelo relatório:
    é de causa conhecida quando TODAS as razões da declaração são de causa conhecida."""
    import study_audit
    out = {}
    for p in prs:
        rows = []
        for f in sorted((reports / str(p["pr"])).glob("*.lean.json")):
            rep = json.loads(f.read_text(encoding="utf-8"))
            opts = {x["line"]: x.get("option") or "" for x in rep["file_findings"]["stage_a_candidates"]
                    if x["code"] == "set_option"}
            for d in rep["declarations"]:
                if d["overall_status"] == "verified":
                    continue
                reasons = [(x["code"], x.get("detail") or {}) for x in d["proof_status"]["reasons"]]
                known = bool(reasons) and all(study_audit.known_cause(c, det, opts) for c, det in reasons)
                rows.append({"file": f.name.removesuffix(".json"), "declaration": d["declaration_name"].split(".0.", 1)[-1],
                             "reasons": [c for c, _ in reasons], "known_cause": known})
        out[str(p["pr"])] = rows
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("prs"); x.add_argument("--selection", type=Path, required=True); x.add_argument("--out", type=Path, required=True)
    x = sub.add_parser("assign")
    x.add_argument("--prs", type=Path, required=True); x.add_argument("--reviewers", type=Path, required=True)
    x.add_argument("--seed", type=int, required=True); x.add_argument("--out", type=Path, required=True)
    x = sub.add_parser("forms"); x.add_argument("--assignment", type=Path, required=True); x.add_argument("--out", type=Path, required=True)
    x = sub.add_parser("alerts")
    x.add_argument("--reports", type=Path, required=True); x.add_argument("--prs", type=Path, required=True)
    x.add_argument("--out", type=Path, required=True)
    x = sub.add_parser("report")
    for k in ("assignment", "forms", "alerts", "defects", "out"):
        x.add_argument(f"--{k}", type=Path, required=True)
    a = ap.parse_args(argv)
    rd = lambda p: json.loads(p.read_text(encoding="utf-8"))
    wr = lambda p, d: p.write_bytes((json.dumps(d, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    if a.cmd == "prs":
        res = select_prs(rd(a.selection)); wr(a.out, res)
        print(" ".join(f"#{r['pr']}({r['stratum']})" for r in res))
    elif a.cmd == "assign":
        res = assign(rd(a.prs), rd(a.reviewers), a.seed); wr(a.out, res)
        print(json.dumps({"attempt": res["attempt"], "load": res["load"], "conditions": res["conditions"]}))
    elif a.cmd == "alerts":
        res = collect_alerts(a.reports, rd(a.prs)); wr(a.out, res)
        print({k: (len(v), sum(x["known_cause"] for x in v)) for k, v in res.items()})
    elif a.cmd == "forms":
        for p in write_forms(rd(a.assignment), a.out):
            print(p)
    else:
        res = report(rd(a.assignment), read_forms(a.forms), rd(a.alerts), rd(a.defects)); wr(a.out, res)
        print(json.dumps(res["summary"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
