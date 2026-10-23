"""`@[implemented_by]`/`@[extern]` escritos × gerados num projeto inteiro (Fase 1, P0-1).

Uso (no fork de medição, depois de `lake exe cache get`; ver `docs/p0-1-implemented-by.md`):
    lake env implemented_by_scan dump Mathlib dump.json
    python tools/phase1/implemented_by_measure.py classify . dump.json --seeds seeds.json --json cls.json
    lake env implemented_by_scan reach Mathlib seeds.json reach.json
    python tools/phase1/implemented_by_measure.py report cls.json reach.json --json p0-1.json --md p0-1.md

`classify`: para cada constante com atributo, o nível TCB/usuário pela MESMA regra do auditor
(`tcb_boundary.classify`, Q7: raiz do toolchain + `lake-manifest.json`, nunca o nome) e, para as
de usuário, a origem:
  * `source_written`  o arquivo do módulo escreve `implemented_by X` (token léxico, mesma
                      varredura da Etapa A) com X igual à implementação (último componente);
  * `generated_ctor_idx`  não escrito, e com a forma do `ctorIdx` gerado pelo Lean (verificada
                      pelo scanner no ambiente, não pelo nome);
  * `generated_type_name` não escrito: `opaque inst` com `@[implemented_by instImpl]` de
                      `deriving TypeName` (`Lean/Elab/Deriving/TypeName.lean:25`);
  * `generated_other` não escrito e sem forma conhecida: gerado por macro/elaborador do próprio
                      projeto ou de dependência. Vai com a linha do fonte onde a constante nasce.
`@[extern]` de usuário é a categoria `extern_user`; constante cuja fronteira não se resolve,
`boundary_unresolved`. As sementes do `reach` são as constantes de usuário e as não resolvidas
(as do toolchain são TCB e não disparam regra).

`report`: junta as duas saídas. Para as declarações reportáveis da raiz, quantas alcançam cada
categoria e quantas só alcançam atributos gerados (as que cairiam só por geração).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from auditor import tcb_boundary as tb  # noqa: E402
from auditor.tier1 import stage_a  # noqa: E402

CATEGORIES = ["source_written", "generated_ctor_idx", "generated_type_name", "generated_other",
              "extern_user", "boundary_unresolved"]
GENERATED = {"generated_ctor_idx", "generated_type_name", "generated_other"}


def base_name(n: str) -> str:
    """Nome sem escopos de macro (`instImpl._@.M._hyg.8` → `instImpl`)."""
    return n.split("._@.")[0]


def last(n: str) -> str:
    return base_name(n).rsplit(".", 1)[-1]


def source_file(project: Path, module: str) -> Path | None:
    rel = Path(*module.split(".")).with_suffix(".lean")
    cands = [project / rel] + sorted((project / ".lake" / "packages").glob(f"*/{rel.as_posix()}"))
    return next((c for c in cands if c.is_file()), None)


def package_of(olean: str | None) -> str:
    if not olean:
        return "?"
    parts = Path(olean).parts
    if "packages" in parts:
        i = parts.index("packages")
        if i + 1 < len(parts):
            return parts[i + 1]
    return "(projeto)"


class SourceIndex:
    """Atributos escritos por arquivo, pela varredura léxica (comentários e strings não contam)."""

    def __init__(self, project: Path):
        self.project = project
        self.cache: dict[str, tuple[set[str], bool, list[str]] | None] = {}

    def get(self, module: str):
        if module not in self.cache:
            f = source_file(self.project, module)
            if f is None:
                self.cache[module] = None
            else:
                text = f.read_text(encoding="utf-8")
                try:
                    toks = stage_a.lex(text)
                except stage_a.LexError:
                    toks = []
                impls = {last(toks[k + 1].text) for k, t in enumerate(toks[:-1])
                         if t.kind == "ident" and not t.quoted and t.text == "implemented_by"
                         and toks[k + 1].kind == "ident"}
                has_extern = any(t.kind == "ident" and not t.quoted and t.text == "extern" for t in toks)
                self.cache[module] = (impls, has_extern, text.split("\n"))
        return self.cache[module]


def classify(project: Path, dump: dict) -> dict:
    lean = shutil.which("lean")
    sysroot = Path(subprocess.run([lean, "--print-prefix"], cwd=project, capture_output=True, text=True,
                                  encoding="utf-8", check=True).stdout.strip())
    b = tb.load_boundary(project, sysroot)
    idx = SourceIndex(project)
    rows = []
    for a in dump["attributed"]:
        level, reason = tb.classify(b, a.get("module") or "", a.get("olean"))
        row = {**a, "level": level, "level_reason": reason,
               "package": "toolchain" if level == tb.TCB else package_of(a.get("olean"))}
        cats = []
        if level == tb.UNRESOLVED:
            cats.append("boundary_unresolved")
        elif level == tb.USER:
            src = idx.get(a["module"]) if a.get("module") else None
            row["source_found"] = src is not None
            if a.get("implementation"):
                if src is not None and last(a["implementation"]) in src[0]:
                    cats.append("source_written")
                elif a.get("ctor_idx_shape"):
                    cats.append("generated_ctor_idx")
                elif last(a["name"]) == "inst" and last(a["implementation"]) == "instImpl" \
                        and a.get("implementation_head") == "TypeName.mk":
                    cats.append("generated_type_name")
                else:
                    cats.append("generated_other")
                    if src is not None and a.get("range"):
                        row["origin_line"] = src[2][a["range"][0] - 1].strip()[:160]
            if a.get("extern"):
                cats.append("extern_user")
                row["extern_in_source"] = bool(src and src[1])
        row["categories"] = cats
        rows.append(row)
    seeds = {r["name"]: CATEGORIES.index(c) for r in rows for c in r["categories"]}
    # uma constante com dois atributos semeia as duas categorias: o `reach` recebe uma por vez
    multi = {r["name"]: r["categories"] for r in rows if len(r["categories"]) > 1}
    table: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        attr = "implemented_by" if r.get("implementation") else "extern"
        for c in r["categories"] or [f"tcb:{attr}"]:
            table[c][r["package"]] += 1
    other = Counter(r.get("origin_line", "(sem faixa no fonte)").split(" ")[0]
                    for r in rows if "generated_other" in r["categories"])
    return {"root": dump["root"], "constants": dump["constants"], "reportable_in_root": dump["reportable_in_root"],
            "categories": CATEGORIES, "by_category_and_package": {c: dict(v) for c, v in sorted(table.items())},
            "generated_other_first_token": dict(other.most_common()),
            "multi_category": multi, "seeds": seeds, "rows": rows}


def report(cls: dict, reach: dict) -> dict:
    assert reach["categories"] == cls["categories"]
    total = reach["reportable_in_root"]
    reach_any = sum(m["count"] for m in reach["masks"] if m["mask"])
    per_cat = {c: sum(m["count"] for m in reach["masks"] if c in m["categories"]) for c in CATEGORIES}
    only_generated = sum(m["count"] for m in reach["masks"] if m["mask"] and set(m["categories"]) <= GENERATED)
    only_ctor_idx = sum(m["count"] for m in reach["masks"] if m["categories"] == ["generated_ctor_idx"])
    pct = (lambda n: round(100 * n / total, 3) if total else None)
    attrs = Counter(c for r in cls["rows"] for c in r["categories"])
    return {
        "root": cls["root"], "reportable_in_root": total,
        "attributed_constants": len(cls["rows"]),
        "user_level_constants_by_category": dict(attrs),
        "by_category_and_package": cls["by_category_and_package"],
        "generated_other_first_token": cls["generated_other_first_token"],
        "declarations_reaching_any": reach_any, "declarations_reaching_any_pct": pct(reach_any),
        "declarations_reaching_category": per_cat,
        "declarations_reaching_category_pct": {c: pct(n) for c, n in per_cat.items()},
        "declarations_reaching_only_generated": only_generated,
        "declarations_reaching_only_generated_pct": pct(only_generated),
        "declarations_reaching_only_ctor_idx": only_ctor_idx,
        "declarations_reaching_only_ctor_idx_pct": pct(only_ctor_idx),
        "masks": reach["masks"], "areas": reach["areas"], "missing_seeds": reach["missing_seeds"],
    }


def to_md(r: dict) -> str:
    out = [f"Raiz `{r['root']}`: {r['reportable_in_root']} declarações reportáveis; "
           f"{r['attributed_constants']} constantes com `implemented_by`/`extern` no ambiente.", "",
           "| categoria | constantes de usuário | declarações que alcançam | % das reportáveis |",
           "|---|---|---|---|"]
    for c in CATEGORIES:
        out.append(f"| {c} | {r['user_level_constants_by_category'].get(c, 0)} | "
                   f"{r['declarations_reaching_category'][c]} | {r['declarations_reaching_category_pct'][c]} |")
    out += ["", f"Alcançam qualquer categoria: {r['declarations_reaching_any']} "
                f"({r['declarations_reaching_any_pct']} %). Só atributos gerados: "
                f"{r['declarations_reaching_only_generated']} ({r['declarations_reaching_only_generated_pct']} %). "
                f"Só `ctorIdx` gerado: {r['declarations_reaching_only_ctor_idx']} "
                f"({r['declarations_reaching_only_ctor_idx_pct']} %).", "",
            "**Por categoria e pacote (constantes)**", ""]
    for c, v in r["by_category_and_package"].items():
        out.append(f"- {c}: " + ", ".join(f"{p} {n}" for p, n in sorted(v.items())))
    if r["generated_other_first_token"]:
        out += ["", "**`generated_other`: primeiro token da linha de origem**", ""]
        out += [f"- `{k}`: {v}" for k, v in r["generated_other_first_token"].items()]
    out += ["", "| máscara | declarações | exemplos |", "|---|---|---|"]
    for m in r["masks"]:
        if m["mask"]:
            out.append(f"| {', '.join(m['categories'])} | {m['count']} | {', '.join(m['examples'][:5])} |")
    return "\n".join(out) + "\n"


def constant_kind(name: str, reason: str) -> str:
    """L-35: `extern`; `generated` (auxiliar de macro, `_aux_…`, como os `…_delab_app_…` de
    `notation`/`notation3`: gerado pelo toolchain ou por comando de sintaxe); `handwritten` (escrito
    pelo autor: `@[delab]`, `@[positivity]`, `initialize`…)."""
    if reason == "extern":
        return "extern"
    return "generated" if "_aux_" in name else "handwritten"


def l35(execcap: dict, causes: dict) -> dict:
    """Alcance da regra por ambiente da L-33a no Mathlib, e o custo MARGINAL: arquivos que a Etapa A
    aceita e que caem só por ela (o efeito no auditor é de arquivo inteiro)."""
    clean = {f["file"] for f in causes["files"] if f["clean"]}
    total_mods, total_rep = execcap["modules_in_root"], execcap["reportable_in_root"]
    rows = []
    for m in execcap["flagged_modules"]:
        kinds = sorted({constant_kind(c["name"], c["reason"]) for c in m["flagged"]})
        file = m["module"].replace(".", "/") + ".lean"
        rows.append({"module": m["module"], "reportable": m["reportable"], "kinds": kinds,
                     "stage_a_clean": file in clean, "examples": [c["name"] for c in m["flagged"][:4]]})
    def agg(sel):
        rs = [r for r in rows if sel(r)]
        return {"modules": len(rs), "reportable": sum(r["reportable"] for r in rs)}
    pct = (lambda n, d: round(100 * n / d, 3) if d else None)
    out = {"modules_in_root": total_mods, "reportable_in_root": total_rep,
           "flagged": agg(lambda r: True),
           "flagged_handwritten": agg(lambda r: "handwritten" in r["kinds"]),
           "flagged_generated_only": agg(lambda r: r["kinds"] == ["generated"]),
           "flagged_extern": agg(lambda r: "extern" in r["kinds"]),
           "marginal": agg(lambda r: r["stage_a_clean"]),
           "marginal_handwritten": agg(lambda r: r["stage_a_clean"] and "handwritten" in r["kinds"]),
           "marginal_generated_only": agg(lambda r: r["stage_a_clean"] and r["kinds"] == ["generated"])}
    for k in [k for k in out if isinstance(out[k], dict)]:
        out[k]["modules_pct"] = pct(out[k]["modules"], total_mods)
        out[k]["reportable_pct"] = pct(out[k]["reportable"], total_rep)
    out["rows"] = rows
    return out

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("project", type=Path)
    c.add_argument("dump", type=Path)
    c.add_argument("--seeds", type=Path, required=True)
    c.add_argument("--json", type=Path, required=True)
    r = sub.add_parser("report")
    r.add_argument("cls", type=Path)
    r.add_argument("reach", type=Path)
    r.add_argument("--json", type=Path, required=True)
    r.add_argument("--md", type=Path)
    x = sub.add_parser("l35")
    x.add_argument("execcap", type=Path)
    x.add_argument("--causes", type=Path, required=True)
    x.add_argument("--json", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "l35":
        res = l35(json.loads(a.execcap.read_text(encoding="utf-8")), json.loads(a.causes.read_text(encoding="utf-8")))
        a.json.write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        print(json.dumps({k: v for k, v in res.items() if k != "rows"}, ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "classify":
        res = classify(a.project.resolve(), json.loads(a.dump.read_text(encoding="utf-8")))
        a.seeds.write_bytes(json.dumps({"categories": CATEGORIES, "seeds": res["seeds"]}).encode("utf-8"))
        a.json.write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        print(json.dumps({k: res[k] for k in ("by_category_and_package", "generated_other_first_token")},
                         ensure_ascii=False, indent=1))
        return 0
    res = report(json.loads(a.cls.read_text(encoding="utf-8")), json.loads(a.reach.read_text(encoding="utf-8")))
    a.json.write_bytes((json.dumps(res, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    md = to_md(res)
    if a.md:
        a.md.write_bytes(md.encode("utf-8"))
    sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
