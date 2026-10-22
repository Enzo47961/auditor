"""Seleção determinística das "provas corretas difíceis" do benchmark (Fase 1, sub-fase 1b).

Uso:
    python tools/phase1/benchmark_select.py <raiz-do-projeto> --causes p0-2-all.json [--n 35]
        [--sample 800] [--json saida.json]

População (instrução 25): arquivos da biblioteca que a Etapa A aceita (`clean` na saída de
`tools/phase1/stage_a_causes.py` sobre a biblioteca inteira), fora da infraestrutura (`Tactic/`,
`Lean/`, `Util/`, `Mathport/`, `Deprecated/`, `Testing/`) — o top-60 por fanout é estruturalmente
fail-closed (L-30). Amostra determinística: os `--sample` primeiros arquivos na ordem do SHA-256 do
caminho. "Difícil" é aproximado pelo comprimento da prova (linhas até a próxima linha na coluna 0,
≥ 15):
proxy declarado, não medida de dificuldade. No máximo um teorema por arquivo e `--per-area` por
área, em rodízio entre áreas; teoremas `private` ficam de fora (o nome no relatório é interno).
Só lê texto (léxico da Etapa A); não compila nada.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from auditor.tier1 import stage_a  # noqa: E402

EXCLUDED_AREAS = {"Tactic", "Lean", "Util", "Mathport", "Deprecated", "Testing"}
MIN_LINES = 15


def candidates(root: Path, rel: str) -> list[dict]:
    text = (root / rel).read_text(encoding="utf-8")
    try:
        toks = stage_a.lex(text)
    except stage_a.LexError:
        return []
    res = stage_a.StageAResult(file=rel, toolchain=None, allowlist=None)
    stage_a._scan_tokens(toks, None, res)
    lines = text.split("\n")
    decls = sorted(res.declarations, key=lambda d: d.line)
    out = []
    for i, d in enumerate(decls):
        kw, name = d.detail.get("keyword"), d.detail.get("name")
        if kw not in ("theorem", "lemma") or not name:
            continue
        # fim da prova: próxima linha não vazia na coluna 0 que não continua o termo (no Mathlib, o
        # corpo da prova é indentado); no máximo até a próxima declaração
        stop = decls[i + 1].line if i + 1 < len(decls) else len(lines) + 1
        end = next((k for k in range(d.line + 1, stop) if lines[k - 1].strip()
                    and lines[k - 1][0] not in " 	|)]}⟩"), stop)
        head = lines[d.line - 1][: d.col]
        if "private" in head or "private" in (lines[d.line - 2] if d.line >= 2 else ""):
            continue
        if end - d.line >= MIN_LINES:
            out.append({"file": rel, "module": rel[:-5].replace("/", "."), "name": name, "line": d.line,
                        "length_lines": end - d.line, "area": rel.split("/")[1]})
    return out


def select(root: Path, clean: list[str], n: int, sample: int, per_area: int) -> dict:
    pool = sorted((f for f in clean if f.count("/") >= 2 and f.split("/")[1] not in EXCLUDED_AREAS),
                  key=lambda f: hashlib.sha256(f.encode("utf-8")).hexdigest())[:sample]
    by_area: dict[str, list[dict]] = defaultdict(list)
    for rel in pool:
        c = candidates(root, rel)
        if c:
            by_area[c[0]["area"]].append(max(c, key=lambda x: (x["length_lines"], x["name"])))
    for a in by_area:
        by_area[a].sort(key=lambda x: (-x["length_lines"], x["file"]))
    chosen, round_ = [], 0
    while len(chosen) < n and round_ < per_area:
        for a in sorted(by_area):
            if round_ < len(by_area[a]) and len(chosen) < n:
                chosen.append(by_area[a][round_])
        round_ += 1
    return {"population": "Etapa A limpa, biblioteca inteira, fora de " + ", ".join(sorted(EXCLUDED_AREAS)),
            "population_files": len([f for f in clean if f.count("/") >= 2
                                     and f.split("/")[1] not in EXCLUDED_AREAS]),
            "sample": len(pool), "min_lines": MIN_LINES, "per_area": per_area,
            "areas_with_candidates": len(by_area), "selected": chosen}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path)
    ap.add_argument("--causes", type=Path, required=True)
    ap.add_argument("--n", type=int, default=35)
    ap.add_argument("--sample", type=int, default=800)
    ap.add_argument("--per-area", type=int, default=4)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    causes = json.loads(a.causes.read_text(encoding="utf-8"))
    clean = [f["file"] for f in causes["files"] if f["clean"]]
    out = select(a.project, clean, a.n, a.sample, a.per_area)
    out["provenance"] = causes.get("provenance")
    out["stage_a_version"] = causes.get("stage_a_version")
    text = json.dumps(out, ensure_ascii=False, indent=1) + "\n"
    if a.json:
        a.json.write_bytes(text.encode("utf-8"))
    for s in out["selected"]:
        print(f"{s['area']:<22} {s['length_lines']:>4}  {s['name']}  ({s['file']}:{s['line']})")
    print(f"{len(out['selected'])} selecionados; amostra {out['sample']} de {out['population_files']} arquivos; "
          f"{out['areas_with_candidates']} áreas com candidatos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
