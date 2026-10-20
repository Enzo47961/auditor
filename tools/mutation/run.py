"""Executor do catálogo de mutações (docs/maintenance.md, "Testes de mutação").

Uso: python tools/mutation/run.py [grupo ...]      (sem argumentos: todos os grupos)

Para cada mutação: aplica no arquivo, roda os testes do grupo com `-x`, e restaura o
arquivo a partir de uma cópia em memória (também em caso de erro ou Ctrl-C). Exit 1 se
alguma mutação sobreviveu ou foi pulada (padrão ausente): as duas coisas exigem ação.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalog import GROUPS  # noqa: E402


def run_group(name: str) -> tuple[int, int, int]:
    g = GROUPS[name]
    detected = survived = skipped = 0
    for rel, old, new in g["mutations"]:
        path = ROOT / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        label = f"{name} | {rel} | {old.splitlines()[0][:70]!r}"
        if text.count(old) != 1:
            print(f"PULADA      | {label}", flush=True)
            skipped += 1
            continue
        try:
            path.write_bytes(text.replace(old, new).encode("utf-8"))
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *g["tests"]],
                               cwd=ROOT, capture_output=True)
        finally:
            path.write_bytes(original)
        if r.returncode != 0:
            detected += 1
            print(f"DETECTADA   | {label}", flush=True)
        else:
            survived += 1
            print(f"SOBREVIVEU  | {label}", flush=True)
    return detected, survived, skipped


def main(argv: list[str]) -> int:
    names = argv or list(GROUPS)
    unknown = [n for n in names if n not in GROUPS]
    if unknown:
        print(f"grupos desconhecidos: {unknown}; existentes: {list(GROUPS)}", file=sys.stderr)
        return 2
    total = [0, 0, 0]
    for n in names:
        for i, v in enumerate(run_group(n)):
            total[i] += v
    print(f"TOTAL: {total[0]} detectadas, {total[1]} sobreviventes, {total[2]} puladas", flush=True)
    return 0 if total[1] == total[2] == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
