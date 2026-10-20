"""Tempos da camada 2 por `cache_state`, a partir dos `outcome.json` baixados das execuções.

Uso:
    python tools/layer2/timings.py <outcome.json | diretório> ... [--json saida.json]

Para cada `cache_state` (cold, delta, warm): número de execuções, mediana e máximo do tempo
total do PR (`elapsed_s`, do trigger ao relatório), da preparação e da auditoria, e o p95 do
tempo por arquivo (base para reajustar `--timeout-file`, instrução 11). Execuções `first_run`
aparecem separadas: não medem o steady-state. Outcome fora do formato é erro (exit 2), não é
ignorado em silêncio.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

SCHEMA = "auditor-ci-outcome/2"
STATES = ("cold", "delta", "warm")


class OutcomeError(Exception):
    pass


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    return s[max(0, math.ceil(0.95 * len(s)) - 1)]


def load(paths: list[Path]) -> list[dict]:
    found = []
    for p in paths:
        found += sorted(p.rglob("outcome.json")) if p.is_dir() else [p]
    out = []
    for f in found:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise OutcomeError(f"{f}: ilegível ({e})")
        if not isinstance(d, dict) or d.get("schema") != SCHEMA or d.get("cache_state") not in STATES:
            raise OutcomeError(f"{f}: fora do formato {SCHEMA}")
        d["_path"] = str(f)
        out.append(d)
    return out


def summarize(outcomes: list[dict]) -> dict:
    res = {}
    for state in STATES:
        runs = [o for o in outcomes if o["cache_state"] == state]
        if not runs:
            continue
        files = [f["duration_s"] for o in runs for f in o["files"]
                 if f.get("exit_code") is not None or f.get("status") == "timeout"]
        res[state] = {
            "runs": len(runs),
            "first_run": sum(1 for o in runs if o.get("first_run")),
            "infra_failed": sum(1 for o in runs if o.get("infra_failed")),
            "elapsed_median_s": round(statistics.median(o["elapsed_s"] for o in runs), 3),
            "elapsed_max_s": round(max(o["elapsed_s"] for o in runs), 3),
            "setup_median_s": round(statistics.median(o["setup_elapsed_s"] for o in runs), 3),
            "audit_median_s": round(statistics.median(o["audit_elapsed_s"] for o in runs), 3),
            "files_audited": len(files),
            "file_p95_s": p95(files),
            "within_steady_state_budget": sum(1 for o in runs if o["elapsed_s"] <= o["steady_state_budget_s"]),
        }
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="timings")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        outcomes = load([Path(p) for p in a.paths])
    except OutcomeError as e:
        sys.stderr.write(f"timings: {e}\n")
        return 2
    s = summarize(outcomes)
    if a.json:
        Path(a.json).write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
    print("| cache_state | execuções | first_run | infra | total mediana (s) | total máx (s) | "
          "preparação mediana (s) | auditoria mediana (s) | arquivos | p95 por arquivo (s) | ≤ 5 min |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for state, r in s.items():
        print(f"| {state} | {r['runs']} | {r['first_run']} | {r['infra_failed']} | {r['elapsed_median_s']} | "
              f"{r['elapsed_max_s']} | {r['setup_median_s']} | {r['audit_median_s']} | {r['files_audited']} | "
              f"{'—' if r['file_p95_s'] is None else r['file_p95_s']} | {r['within_steady_state_budget']}/{r['runs']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
