"""Proporção de declarações de um projeto Lake que usam avaliação nativa (instrução 13).

Uso (camada 2, passo 6 do checklist):
    python tools/layer2/native_usage.py <raiz-do-projeto> --root Mathlib [--json saida.json]

Pergunta medida: se `native_decide` nunca sai `verified` na Fase 0 (Q9-a), quanto do projeto-alvo
isso atinge, e onde. Contagem LÉXICA, com o lexer e a regra de detecção da própria Etapa A
(comentários e strings não contam): `native_decide`, `+native`, `native := …` (mesmo achado
`native_decide` da Etapa A) e `bv_decide`. Cada ocorrência é atribuída à declaração que a contém:
a última que começa num comando na coluna 0 antes dela (pulando docstring, `@[…]` e modificadores).
É estimativa, não o veredito: o veredito por declaração é o do auditor (`native_auxiliary_axiom`),
que vale também para táticas que chamam `nativeEqTrue` sem nenhuma dessas palavras.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from auditor.tier1 import stage_a  # noqa: E402

BODY_KINDS = {"theorem", "lemma", "example", "def", "abbrev", "instance", "opaque"}


def _decl_starts(toks: list) -> list[tuple[int, str]]:
    """(índice do token, tipo) das declarações com corpo que começam um comando na coluna 0."""
    out, prev_line = [], 0
    for k, t in enumerate(toks):
        first, prev_line = t.line != prev_line, t.line
        if not (first and t.col == 0):
            continue
        j = k
        while j < len(toks):
            u = toks[j]
            if u.kind == "doc" or (u.kind == "ident" and u.text in stage_a.MODIFIERS):
                j += 1
            elif u.kind == "symbol" and u.text == "@[":
                depth, j = 1, j + 1
                while j < len(toks) and depth:
                    depth += toks[j].text in ("[", "@[")
                    depth -= toks[j].text == "]"
                    j += 1
            else:
                break
        if j < len(toks) and toks[j].kind == "ident" and toks[j].text in BODY_KINDS and not toks[j].quoted \
                and (not out or out[-1][0] != j):   # docstring na coluna 0 e `theorem` na linha seguinte
            out.append((j, toks[j].text))
    return out


def scan_file(src: str) -> dict:
    toks = stage_a.lex(src)
    res = stage_a.StageAResult(file="", toolchain=None, allowlist=None)
    stage_a._scan_tokens(toks, None, res)
    hits = [(f.line, f.col, f.detail["form"]) for f in res.findings if f.code == "native_decide"]
    hits += [(t.line, t.col, "bv_decide") for t in toks
             if t.kind == "ident" and not t.quoted and t.text == "bv_decide"]
    starts = _decl_starts(toks)
    pos = [(toks[k].line, toks[k].col) for k, _ in starts]
    native_decls: set[int] = set()
    forms: dict[str, int] = defaultdict(int)
    for line, col, form in hits:
        forms[form] += 1
        owner = max((i for i, p in enumerate(pos) if p <= (line, col)), default=None)
        if owner is not None:
            native_decls.add(owner)
    return {"declarations": len(starts), "native_declarations": len(native_decls),
            "occurrences": len(hits), "forms": dict(forms)}


def measure(project: Path, root: str) -> dict:
    files = sorted((project / root).rglob("*.lean"))
    if (project / f"{root}.lean").is_file():
        files.append(project / f"{root}.lean")
    areas: dict[str, dict] = defaultdict(lambda: {"files": 0, "declarations": 0, "native_declarations": 0,
                                                   "occurrences": 0})
    native_files, errors = [], []
    forms: dict[str, int] = defaultdict(int)
    for f in files:
        rel = f.relative_to(project)
        area = "/".join(rel.parts[:2]) if len(rel.parts) > 2 else rel.parts[0]
        try:
            r = scan_file(f.read_text(encoding="utf-8"))
        except stage_a.LexError as e:
            errors.append({"file": rel.as_posix(), "error": str(e)})
            continue
        a = areas[area]
        a["files"] += 1
        for key in ("declarations", "native_declarations", "occurrences"):
            a[key] += r[key]
        for k, v in r["forms"].items():
            forms[k] += v
        if r["occurrences"]:
            native_files.append({"file": rel.as_posix(), **r})
    total = {k: sum(a[k] for a in areas.values()) for k in ("files", "declarations", "native_declarations",
                                                             "occurrences")}
    total["proportion"] = total["native_declarations"] / total["declarations"] if total["declarations"] else 0.0
    return {"root": root, "total": total, "forms": dict(sorted(forms.items())),
            "areas": {k: areas[k] for k in sorted(areas)}, "native_files": native_files, "lex_errors": errors}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="native_usage")
    ap.add_argument("project")
    ap.add_argument("--root", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    m = measure(Path(a.project), a.root)
    if a.json:
        Path(a.json).write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    t = m["total"]
    print(f"{t['files']} arquivos, {t['declarations']} declarações com corpo em {a.root}; "
          f"{t['native_declarations']} usam avaliação nativa ({t['proportion']:.4%}); "
          f"{t['occurrences']} ocorrências {m['forms']}")
    used = {k: v for k, v in m["areas"].items() if v["native_declarations"]}
    if used:
        print("| Área | declarações | com avaliação nativa | proporção |\n|---|---|---|---|")
        for k, v in sorted(used.items(), key=lambda kv: -kv[1]["native_declarations"]):
            print(f"| `{k}` | {v['declarations']} | {v['native_declarations']} | "
                  f"{v['native_declarations'] / v['declarations']:.2%} |")
    if m["lex_errors"]:
        print(f"{len(m['lex_errors'])} arquivos com erro de lexer (não contados): "
              f"{[e['file'] for e in m['lex_errors'][:10]]}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
