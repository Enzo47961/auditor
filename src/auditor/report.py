"""Montagem do relatório v1 e do exit code.

Exit codes (README; Q6):
  0 — toda declaração `verified`, nenhuma entrada não reconhecida no arquivo;
  1 — alguma declaração não `verified`, alvo que não compila (Q6) ou conteúdo não reconhecido;
  2 — a ferramenta não conseguiu rodar: política inválida, ambiente não fixado ou
      inconsistente, timeout, falha do inspetor; ou arquivo sem declarações
      (`no_declarations_found`, D-15 revisada), salvo com `--allow-empty`.
Exit 0 nunca sai com input não reconhecido.
"""
from __future__ import annotations

import hashlib
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import auditor
from auditor import aggregator as ag
from auditor.fingerprint import build_tcb, is_complete

SCHEMA_VERSION = "1.1.0"   # 1.1: tcb.classification_review_status (L-26)


def _decl_hash(d: dict) -> str:
    parts = (d["name"], d.get("kind") or "", d.get("type_hash") or "", d.get("value_hash") or "")
    return "sha256:" + hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def seal(decl: dict, fp: str | None) -> str:
    return (f"auditor Tier1 v{auditor.__version__} · Prova: {decl['proof_status']['value']} · "
            f"Premissas: {decl['premises_status']['value']} · Correspondência: Não Auditada · "
            f"Não coberto: {', '.join(ag.NOT_COVERED)} · fingerprint: {fp or 'indisponível'}")


def build(target: Path, sa, sb, policy, policy_error: str | None, *, started: float,
          timeout_s: float, timeout_test: str | None, allow_empty: bool = False,
          dependency_execution: list[dict] | None = None) -> tuple[dict, int]:
    infra: list[dict] = []
    file_unrecognized: list[dict] = []
    a_names = ag.stage_a_names(sa)
    root = Path(sb.project_root) if sb and sb.project_root else None

    def unelaborated(code, detail=None):
        return [ag.unelaborated_declaration(n, v["keyword"], code, detail) for n, v in a_names.items()]

    for u in sa.unrecognized:
        item = {"code": u.code, "line": u.line, **u.detail}
        (infra if u.code in ag.STAGE_A_INFRA else file_unrecognized).append(item)

    compilation = dict(sb.build) if sb else {"status": "not_run"}
    compilation.pop("log_tail", None)
    facts_by_name: dict[str, dict] = {}

    if policy_error is not None:
        infra.append({"code": "policy_invalid", "detail": policy_error})
        decls = unelaborated("policy_invalid", {"detail": policy_error})
    elif sb is None or sb.unrecognized:
        codes = [u["code"] for u in (sb.unrecognized if sb else [])] or ["stage_b_not_run"]
        infra += sb.unrecognized if sb else [{"code": "stage_b_not_run"}]
        decls = unelaborated("infrastructure_failure", {"codes": codes})
    elif sb.tampered:   # L-33 (b): violação de conteúdo, não falha de infraestrutura
        file_unrecognized.append({"code": "toolchain_tampered", **sb.tampered})
        decls = unelaborated("toolchain_tampered", sb.tampered)
    elif sb.build["status"] == "timeout":
        infra.append({"code": "timeout", "detail": {"timeout_s": timeout_s}})
        decls = unelaborated("timeout", {"timeout_s": timeout_s})
    elif sb.build["status"] != "success":
        file_unrecognized.append({"code": "compile_failure",
                                  "cycle_detected": bool(sb.build.get("cycle_detected"))})
        decls = unelaborated("compile_failure", {"cycle_detected": bool(sb.build.get("cycle_detected"))})
    else:
        decls = None

    tcb = build_tcb(sa, sb, policy, root)
    empty_allowed = False
    if decls is None:
        b_names = [d["name"] for d in sb.declarations]
        reach, hb, so_file = ag.options_in_reach(policy, sa, b_names)
        file_effects = ag.stage_a_file_effects(sa) + ag.stage_a_execution_effects(sa) + so_file \
            + ag.dependency_execution_effects(dependency_execution or []) \
            + ag.execution_capable_effects(sb.execution_capable)
        if any(u["code"] in ag.STAGE_A_INFRA for u in infra):
            file_effects.append(ag.P("unresolved", "stage_a_incomplete"))
        anomalies: dict[str, list] = {}
        for a in sb.anomalies:
            anomalies.setdefault(a["declaration"], []).append(a)
        ctx = ag.Context(policy=policy, file_rel=ag.file_rel_path(target, sb.project_root),
                         owner_docs=sb.owners, file_effects=file_effects, options_by_decl=reach,
                         heartbeat_bound=hb, anomalies_by_decl=anomalies,
                         tcb_complete=is_complete(tcb))
        decls = []
        for d in sb.declarations:
            facts_by_name[d["name"]] = d
            decls.append(ag.evaluate_declaration(ctx, d))
        seen = {ag.user_name(n) for n in b_names}
        for n, v in a_names.items():
            if n not in seen:
                decls.append(ag.unelaborated_declaration(n, v["keyword"], "declaration_not_found_in_environment"))
                file_unrecognized.append({"code": "declaration_not_found_in_environment", "name": n,
                                          "line": v["line"]})
        if not decls:
            # D-15 (revisada pelo revisor): sem declarações não há o que rejeitar. O usuário
            # apontou o arquivo errado, um arquivo só de imports ou um script: exit 2, salvo
            # pedido explícito (`--allow-empty`).
            if allow_empty:
                empty_allowed = True
            else:
                infra.append({"code": "no_declarations_found",
                              "detail": "nenhuma declaração no arquivo; use --allow-empty se for intencional"})

    ag.fill_depends_on_rejected(decls)
    infra_status = "failed" if infra else "ok"
    meta = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(time.monotonic() - started, 3),
        "infrastructure_status": infra_status,
        "compilation": compilation,
        "timeout_s": timeout_s,
        "timeout_test": timeout_test,
        "allow_empty": allow_empty,
        "platform": platform.platform(),
    }
    for d in decls:
        f = facts_by_name.get(d["declaration_name"])
        d["declaration_hash"] = _decl_hash(f) if f else None
        d["seal"] = seal(d, tcb.get("fingerprint"))
        d["tcb"] = tcb
        d["execution_metadata"] = meta

    if infra:
        code = 2
    elif file_unrecognized or any(d["overall_status"] != "verified" for d in decls):
        code = 1
    else:
        code = 0
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "auditor", "tier": "Tier1", "phase": "0", "version": auditor.__version__},
        "target": {"file": str(target), "module": sb.module if sb else None,
                   "project_root": sb.project_root if sb else None},
        "compilation": compilation,
        "infrastructure": {"status": infra_status, "reasons": infra},
        "file_findings": {
            "unrecognized": file_unrecognized,
            "warnings": [{"code": w.code, "line": w.line, **w.detail} for w in sa.warnings]
            + ([{"code": "empty_file_allowed"}] if empty_allowed else []),
            "stage_a_candidates": [{"code": f.code, "line": f.line, **f.detail} for f in sa.findings],
        },
        "declarations": decls,
        "tcb": tcb,
        "not_covered": ag.NOT_COVERED,
        "execution_metadata": meta,
        "exit_code": code,
    }
    return report, code
