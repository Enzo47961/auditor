"""CLI: `auditor check <arquivo.lean> --output report.json --policy policy.toml`.

Fail-closed: todo caminho que não conclui a análise sai com exit ≠ 0 e, sempre que
possível, com relatório explicando a razão. Nunca exit 0 com input não reconhecido.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_INFRA = 0, 1, 2
DEFAULT_TIMEOUT_S = 90.0    # timeout por arquivo (instrução 11, D-21); o orçamento do PR é do auditor-ci


def _utf8_stdio() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def check(args: argparse.Namespace) -> int:
    from auditor import report as rp
    from auditor.policy import PolicyError, load_policy
    from auditor.schema import validation_errors
    from auditor.tier1 import stage_a, stage_b

    started = time.monotonic()
    target = Path(args.file)
    if not target.is_file():
        sys.stderr.write(f"auditor: arquivo não encontrado: {target}\n")
        return EXIT_INFRA

    policy, policy_error = None, None
    try:
        policy = load_policy(Path(args.policy))
    except PolicyError as e:
        policy_error = str(e)

    sa = stage_a.analyze(target, allowlist_file=Path(args.allowlist) if args.allowlist else None)
    sb = None
    if policy_error is None:
        sb = stage_b.analyze(target, timeout_s=args.timeout)
    report, code = rp.build(target, sa, sb, policy, policy_error, started=started,
                            timeout_s=args.timeout, timeout_test=args.timeout_test,
                            allow_empty=args.allow_empty)

    errors = validation_errors(report)
    if errors:   # bug do agregador: nunca entregar relatório fora do schema como se fosse válido
        report["infrastructure"]["status"] = "failed"
        report["infrastructure"]["reasons"].append({"code": "report_schema_invalid", "detail": errors[:20]})
        report["exit_code"] = code = EXIT_INFRA
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    for d in report["declarations"]:
        sys.stderr.write(f"{d['overall_status']:>10}  {d['declaration_name']}  "
                         f"[{d['proof_status']['value']} / {d['premises_status']['value']}]\n")
    for r in report["infrastructure"]["reasons"]:
        sys.stderr.write(f"infraestrutura: {r['code']}\n")
    if errors:
        sys.stderr.write("relatório não passa no schema v1:\n  " + "\n  ".join(errors[:20]) + "\n")
    sys.stderr.write(f"exit {code} — relatório: {out}\n")
    return code


def main(argv: list[str] | None = None) -> int:
    _utf8_stdio()
    ap = argparse.ArgumentParser(prog="auditor", description="Verificador mecânico de integridade "
                                 "de provas Lean 4 — Fase 0, Tier 1. Não audita correspondência.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="audita um arquivo .lean")
    c.add_argument("file")
    c.add_argument("--output", required=True)
    c.add_argument("--policy", required=True)
    c.add_argument("--allowlist", help="allow-list de projeto explícita (padrão: <projeto>/.auditor/allowlist.json)")
    c.add_argument("--timeout-file", "--timeout", dest="timeout", type=float, default=DEFAULT_TIMEOUT_S,
                   help="timeout deste arquivo em segundos (padrão: 90)")
    c.add_argument("--timeout-test", choices=["artificial"], default=None,
                   help="marca o relatório como teste de timeout com limite artificial (L-11)")
    c.add_argument("--allow-empty", action="store_true",
                   help="arquivo sem declarações (ex.: só imports) sai com exit 0 em vez de 2 (D-15)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return EXIT_INFRA if e.code else EXIT_OK
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
