"""Seleção mecânica dos PRs do estudo de usuário (Fase 1, sub-fase 1c; docs/user-study.md, seção 2).

Uso:
    python tools/phase1/study_select.py <worktree-do-mathlib-em-e1b2403b> --base e1b2403b… \\
        --allowlist <.auditor/allowlist.json> --json candidatos.json [--patches dir/]

Para cada commit da `master` do Mathlib depois de `--base`, em ordem de integração (cada commit é um
PR integrado, `(#N)` na mensagem), aplica os critérios publicados ANTES da escolha:
  1. só arquivos `.lean` em `Mathlib/`, de 1 a 5, fora de `Mathlib/Tactic/`, `Mathlib/Lean/`, `Mathlib/Util/`;
     nenhum outro arquivo alterado, exceto documentação (`docs/`, `*.md`);
  2. até 300 linhas de diff (adições + remoções);
  3. o diff do commit aplica sem conflito sobre `--base` (`git apply --check`);
  4. estrato pela Etapa A do auditor sobre os arquivos já com o patch aplicado:
     `success` se todos os alterados são aceitos; `fail_closed` se algum tem item não reconhecido.
A exclusão (B) — `ctorIdx` gerado e opções `backward.*` — depende da auditoria completa e é decidida
depois, pelo relatório do auditor (workflow `auditor-study-select` do repositório de medições).
O worktree é restaurado depois de cada commit (`git apply -R`). Só leitura na API do GitHub.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
from auditor.tier1 import stage_a  # noqa: E402

REPO = "leanprover-community/mathlib4"
EXCLUDED_DIRS = ("Mathlib/Tactic/", "Mathlib/Lean/", "Mathlib/Util/")
MAX_FILES, MAX_LINES = 5, 300


def gh(*args: str, accept: str | None = None, tries: int = 4) -> str:
    cmd = ["gh", "api", *args] + (["-H", f"Accept: {accept}"] if accept else [])
    for k in range(tries):   # a API falha de vez em quando por rede: nova tentativa, com espera
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if p.returncode == 0:
            return p.stdout
        time.sleep(5 * (k + 1))
    raise RuntimeError(f"gh api falhou {tries} vezes: {' '.join(args)}: {p.stderr[-300:]}")


def criteria(files: list[dict]) -> tuple[bool, str]:
    lean = [f for f in files if f["filename"].endswith(".lean")]
    other = [f for f in files if not f["filename"].endswith(".lean")
             and not (f["filename"].startswith("docs/") or f["filename"].endswith(".md"))]
    if other:
        return False, "altera arquivo que não é .lean nem documentação: " + ", ".join(f["filename"] for f in other[:3])
    if not 1 <= len(lean) <= MAX_FILES:
        return False, f"{len(lean)} arquivos .lean (critério: 1 a {MAX_FILES})"
    bad = [f["filename"] for f in lean if not f["filename"].startswith("Mathlib/")
           or f["filename"].startswith(EXCLUDED_DIRS)]
    if bad:
        return False, "fora de Mathlib/ ou em infraestrutura: " + ", ".join(bad[:3])
    if any(f["status"] == "removed" for f in lean):
        return False, "remove arquivo .lean"
    lines = sum(f["additions"] + f["deletions"] for f in files)
    if lines > MAX_LINES:
        return False, f"{lines} linhas de diff (critério: ≤ {MAX_LINES})"
    return True, f"{len(lean)} arquivos, {lines} linhas"


def stratum(worktree: Path, lean_files: list[str], allowlist: Path) -> tuple[str, dict]:
    items = {}
    for rel in lean_files:
        r = stage_a.analyze(worktree / rel, allowlist_file=allowlist)
        items[rel] = [{"code": u.code, "line": u.line, **u.detail} for u in r.unrecognized]
    return ("fail_closed" if any(items.values()) else "success"), items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree", type=Path)
    ap.add_argument("--base", required=True)
    ap.add_argument("--allowlist", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--patches", type=Path)
    a = ap.parse_args(argv)
    wt = a.worktree.resolve()
    head = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    if not head.startswith(a.base[:12]) and not a.base.startswith(head[:12]):
        sys.exit(f"worktree em {head}, esperado {a.base}")
    cmp = json.loads(gh(f"repos/{REPO}/compare/{a.base}...master"))
    out = []
    for c in cmp["commits"]:
        sha, msg = c["sha"], c["commit"]["message"].split("\n")[0]
        pr = re.search(r"\(#(\d+)\)\s*$", msg)
        row = {"sha": sha, "pr": int(pr.group(1)) if pr else None, "title": msg,
               "author": (c.get("author") or {}).get("login"), "merged_at": c["commit"]["committer"]["date"]}
        files = json.loads(gh(f"repos/{REPO}/commits/{sha}"))["files"]
        ok, why = criteria(files)
        row.update({"eligible": ok, "reason": why})
        if ok:
            diff = gh(f"repos/{REPO}/commits/{sha}", accept="application/vnd.github.diff")
            pfile = (a.patches or a.json.parent) / f"{sha[:12]}.diff"
            pfile.parent.mkdir(parents=True, exist_ok=True)
            pfile.write_bytes(diff.encode("utf-8"))
            chk = subprocess.run(["git", "-C", str(wt), "apply", "--check", str(pfile)], capture_output=True, text=True)
            if chk.returncode != 0:
                row.update({"eligible": False, "reason": "não aplica sobre a base: " + chk.stderr.strip()[:200]})
            else:
                subprocess.run(["git", "-C", str(wt), "apply", str(pfile)], check=True)
                try:
                    lean = [f["filename"] for f in files if f["filename"].endswith(".lean")]
                    row["stratum"], row["stage_a"] = stratum(wt, lean, a.allowlist)
                    row["files"] = lean
                    row["patch"] = pfile.name
                finally:
                    subprocess.run(["git", "-C", str(wt), "apply", "-R", str(pfile)], check=True)
        out.append(row)
        print(f"{'OK ' if row['eligible'] else '-- '} #{row['pr']}  {row.get('stratum', ''):<11} {row['reason'][:70]}  {msg[:50]}")
    data = {"repo": REPO, "base": a.base, "criteria": {"max_files": MAX_FILES, "max_lines": MAX_LINES,
                                                       "excluded_dirs": EXCLUDED_DIRS},
            "commits": out, "eligible": sum(r["eligible"] for r in out)}
    a.json.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"{data['eligible']} elegíveis de {len(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
