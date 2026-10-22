"""Causas de fail-closed da Etapa A nos arquivos de maior fanout (Fase 1, P0-2).

Uso:
    python tools/phase1/stage_a_causes.py <raiz-do-projeto> --fanout fanout.json [--top 60]
        [--allowlist <raiz>/.auditor/allowlist.json] [--json saida.json] [--md saida.md]

Roda a Etapa A do auditor (a mesma função `stage_a.analyze` do CI, com a allow-list de projeto)
em cada um dos `--top` primeiros arquivos do ranking de `tools/layer2/fanout.py` e classifica cada
item não reconhecido numa causa:

  (a) `false_positive`   `unknown_command`: token na coluna 0 que não é token inicial de nenhum
                         comando do ambiente (a allow-list é o conjunto inteiro de tokens iniciais
                         da categoria `command` do parser, Lean + projeto). É continuação de termo
                         escrita na coluna 0, ou outro token que não começa comando;
  (b) `non_syntactic`    `metaprogramming_command` ou `unclassified_command`: comando que derruba
                         o arquivo por classificação (L-17, L-25), não por declarar sintaxe;
  (c) `syntax`           `syntax_extension_declared`: o arquivo declara sintaxe;
  (d) `other`            qualquer outro código (Unicode proibido, erro léxico, nome de declaração
                         não resolvido, allow-list ausente ou obsoleta…).

Um arquivo pode ter várias causas. A saída conta arquivos por causa, arquivos cuja ÚNICA causa é
cada uma (o que uma correção daquela causa resgataria sozinha) e ocorrências por token/comando.
Não decide nada: é medição. Determinístico para o mesmo checkout e a mesma allow-list.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from auditor.tier1 import stage_a  # noqa: E402

CAUSES = ("false_positive", "non_syntactic", "syntax", "other")


def cause_of(code: str) -> str:
    if code == "unknown_command":
        return "false_positive"
    if code in ("metaprogramming_command", "unclassified_command"):
        return "non_syntactic"
    if code == "syntax_extension_declared":
        return "syntax"
    return "other"


def key_of(item: stage_a.Item) -> str:
    d = item.detail or {}
    return str(d.get("token") or d.get("command") or item.code)


def scan(project: Path, rows: list[dict], allowlist: Path | None) -> dict:
    files = []
    for rank, row in enumerate(rows, 1):
        path = project / row["file"]
        res = stage_a.analyze(path, allowlist_file=allowlist)
        items = [{"code": u.code, "cause": cause_of(u.code), "key": key_of(u), "line": u.line, "col": u.col}
                 for u in res.unrecognized]
        files.append({"rank": rank, "file": row["file"], "transitive": row.get("transitive"),
                      "clean": not items, "causes": sorted({i["cause"] for i in items}), "items": items})
    return files


def summarize(files: list[dict]) -> dict:
    n = len(files)
    failing = [f for f in files if not f["clean"]]
    by_cause = {c: sum(c in f["causes"] for f in files) for c in CAUSES}
    only = {c: sum(f["causes"] == [c] for f in files) for c in CAUSES}
    keys: dict[str, Counter] = defaultdict(Counter)
    files_per_key: dict[str, Counter] = defaultdict(Counter)
    for f in files:
        seen = set()
        for i in f["items"]:
            keys[i["cause"]][i["key"]] += 1
            if (i["cause"], i["key"]) not in seen:
                seen.add((i["cause"], i["key"]))
                files_per_key[i["cause"]][i["key"]] += 1
    return {
        "files": n, "clean": n - len(failing), "failing": len(failing),
        "fail_closed_rate": round(len(failing) / n, 4) if n else None,
        "files_by_cause": by_cause, "files_only_cause": only,
        "occurrences_by_key": {c: dict(keys[c].most_common()) for c in CAUSES},
        "files_by_key": {c: dict(files_per_key[c].most_common()) for c in CAUSES},
    }


def to_md(files: list[dict], s: dict) -> str:
    out = [f"{s['files']} arquivos; limpos {s['clean']}; fail-closed {s['failing']} "
           f"({100 * (s['fail_closed_rate'] or 0):.1f} %)", "",
           "| causa | arquivos com a causa | arquivos só com a causa |", "|---|---|---|"]
    out += [f"| {c} | {s['files_by_cause'][c]} | {s['files_only_cause'][c]} |" for c in CAUSES]
    for c in CAUSES:
        if s["files_by_key"][c]:
            out += ["", f"**{c}** (token/comando: arquivos, ocorrências)", ""]
            out += [f"- `{k}`: {v} arq., {s['occurrences_by_key'][c][k]} ocorr."
                    for k, v in s["files_by_key"][c].items()]
    out += ["", "| # | arquivo | causas | itens (linha:token) |", "|---|---|---|---|"]
    for f in files:
        its = ", ".join(f"{i['line']}:{i['key']}" for i in f["items"][:8]) + (" …" if len(f["items"]) > 8 else "")
        out.append(f"| {f['rank']} | `{f['file']}` | {', '.join(f['causes']) or 'limpo'} | {its} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--fanout", type=Path, required=True)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--allowlist", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    fan = json.loads(a.fanout.read_text(encoding="utf-8"))
    rows = fan["rows"][: a.top]
    allow = a.allowlist or (a.project / ".auditor" / "allowlist.json")
    files = scan(a.project, rows, allow)
    s = summarize(files)
    data = {"provenance": fan.get("provenance"), "stage_a_version": stage_a.STAGE_A_VERSION,
            "allowlist": str(allow), "top": a.top, "summary": s, "files": files}
    if a.json:
        a.json.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    md = to_md(files, s)
    if a.md:
        a.md.write_bytes(md.encode("utf-8"))
    sys.stdout.write(md if not a.md else md.split("\n\n| # |")[0] + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
