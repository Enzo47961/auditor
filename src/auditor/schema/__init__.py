"""JSON Schema v1 do relatório (publicado em `schema/report-v1.json` na raiz; cópia
empacotada aqui, e um teste trava a divergência entre as duas)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

SCHEMA_FILE = Path(__file__).resolve().parent / "report-v1.json"


@lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def validation_errors(report: dict) -> list[str]:
    from jsonschema import Draft202012Validator
    v = Draft202012Validator(schema())
    return [f"{'/'.join(map(str, e.absolute_path)) or '<raiz>'}: {e.message}"
            for e in sorted(v.iter_errors(report), key=lambda e: list(map(str, e.absolute_path)))]
