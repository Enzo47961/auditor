"""Agregador: aplica a política aos fatos das Etapas A e B e consolida os estados.

Cada regra é uma função pura (fatos + política → efeitos), com teste de regressão
próprio em tests/policy/test_rules.py. Um efeito afeta UM estado (ortogonalidade Q1-X):
  * proof:    "rejected" (Rejeitada) | "unresolved" (Não resolvida)
  * premises: "nonconforming" (Não conforme) | "unresolved" (Não resolvido)
Consolidação dentro de cada estado: pior efeito vence. `overall_status`: tabela da Q4.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from auditor.policy import Policy, parse_justification

PROOF = {"rejected": "Rejeitada", "unresolved": "Não resolvida", None: "Validada"}
PREMISES = {"nonconforming": "Não conforme", "unresolved": "Não resolvido", None: "Conforme"}
CORRESPONDENCE = "Não auditada"
NOT_COVERED = ["correspondência", "kernel", "análise semântica", "contextos construtivos"]
PRIVATE = re.compile(r"^_private\.(?:.+?)\.\d+\.(?P<user>.+)$")


@dataclass
class Effect:
    state: str                      # "proof" | "premises"
    severity: str
    code: str
    detail: dict = field(default_factory=dict)
    violation: dict | None = None   # entrada de `policy_violations`, se a regra é de política


def P(sev, code, detail=None, violation=None):
    return Effect("proof", sev, code, detail or {}, violation)


def M(sev, code, detail=None, violation=None):
    return Effect("premises", sev, code, detail or {}, violation)


def user_name(name: str) -> str:
    m = PRIVATE.match(name)
    return m.group("user") if m else name


def _owners(d: dict, axioms: set[str]) -> list[str | None]:
    out = []
    for ref in d["axiom_referrers"]:
        if ref["axiom"] in axioms:
            out += [r["owner"] for r in ref["referrers"]]
    return sorted(set(out), key=lambda x: (x is None, x or ""))


def _native_axioms(policy: Policy, d: dict) -> set[str]:
    """Axiomas de avaliação nativa da declaração: os da política (`ofReduceBool`, …) e os
    auxiliares por uso da v4.36 (forma reconhecida pelo inspetor)."""
    return (set(d["axioms_official"]) & policy.native_evaluation) | \
        {a["axiom"] for a in d.get("native_auxiliary", [])}


# --------------------------------------------------------------------------- regras

def rule_admissions(policy: Policy, d: dict) -> tuple[list[Effect], list[dict]]:
    """`sorryAx` e similares → proof Rejeitada (Q1-X), com origens rastreadas."""
    effects, admissions = [], []
    for ax in d["axioms_official"]:
        if ax in policy.admissions:
            origins = _owners(d, {ax})
            admissions.append({"name": ax, "origins": origins})
            effects.append(P("rejected", f"{ax}_detected", {"origins": origins}))
    return effects, admissions


def rule_axioms(policy: Policy, d: dict) -> tuple[list[Effect], list[dict], list[dict]]:
    """Classifica cada axioma transitivo. Proibido → Não conforme; desconhecido → lacuna B."""
    effects, listing, warnings = [], [], []
    aux = {a["axiom"]: a for a in d.get("native_auxiliary", [])}
    for ax in d["axioms_official"]:
        if ax in policy.admissions:
            cls = "admission"
        elif ax in policy.native_evaluation:
            cls = "native_evaluation"
        elif ax in aux:
            cls = "native_auxiliary"
            effects.append(M("unresolved", "native_auxiliary_axiom", {
                "axiom": ax, "tactic": aux[ax]["tactic"], "owner": aux[ax]["owner"],
                "action": policy.native_auxiliary_action}))
        elif ax in policy.allowed_axioms:
            cls = "allowed"
        elif ax in policy.forbidden_axioms:
            cls = "forbidden"
            effects.append(M("nonconforming", "forbidden_axiom", {"axiom": ax},
                             {"rule": "forbidden_axiom", "axiom": ax}))
        else:
            cls = "unknown"
            if policy.unknown_axiom_action == "fail_closed":
                effects.append(M("unresolved", "unknown_axiom", {
                    "axiom": ax, "suggestion": f"declarar {ax!r} em axioms.allowed ou axioms.forbidden"}))
            else:
                warnings.append({"code": "unknown_axiom_allowed_with_warning", "axiom": ax,
                                 "justification": policy.unknown_axiom_justification})
        listing.append({"name": ax, "classification": cls, "origins": _owners(d, {ax})})
    return effects, listing, warnings


def rule_native_evaluation(policy: Policy, d: dict, owner_docs: dict) -> list[Effect]:
    """`Lean.ofReduceBool`/`ofReduceNat` exigem justificativa válida na docstring da DONA (O-1/B)."""
    native = _native_axioms(policy, d)
    if not native:
        return []
    effects = []
    for owner in _owners(d, native):
        if owner is None or owner not in owner_docs:
            effects.append(P("unresolved", "native_decide_owner_unresolved", {"owner": owner}))
            continue
        j = parse_justification(owner_docs[owner].get("docstring"))
        if j.status == "absent":
            effects.append(M("nonconforming", "native_decide_unjustified", {"owner": owner},
                             {"rule": "native_decide_unjustified", "owner": owner}))
        elif j.status == "malformed":
            effects.append(M("nonconforming", "native_decide_justification_malformed",
                             {"owner": owner, "detail": j.detail},
                             {"rule": "native_decide_justification_malformed", "owner": owner,
                              "detail": j.detail}))
    return effects


def rule_native_implementations(policy: Policy, d: dict) -> list[Effect]:
    """`@[implemented_by]`/`@[extern]` USER-LEVEL (Q7-a). Sozinho → candidato; com avaliação
    nativa nos axiomas → padrão combinado, Rejeitada. Fronteira indecidível → Não resolvida."""
    native = bool(_native_axioms(policy, d))
    effects = []
    for attr in policy.native_attributes:
        entries = d.get(attr, [])
        unresolved = sorted(e["name"] for e in entries if e.get("level") not in ("tcb", "user"))
        if unresolved:
            effects.append(P("unresolved", "tcb_boundary_unresolved", {"attribute": attr, "constants": unresolved}))
        user = sorted(e["name"] for e in entries if e.get("level") == "user")
        if not user:
            continue
        if native:
            code = f"{attr}_reaches_native_eval"
            effects.append(P("rejected", code, {"constants": user}, {"rule": code, "constants": user}))
        else:
            effects.append(P("unresolved", f"{attr}_candidate", {"constants": user}))
    return effects


def rule_orphan_justification(policy: Policy, d: dict, heartbeat_bound: bool) -> list[Effect]:
    """Justificativa numa declaração que não é dona de avaliação nativa → violação (Q3b)."""
    j = parse_justification(d.get("docstring"))
    if j.status == "absent" or heartbeat_bound:
        return []
    owned = set(_owners(d, _native_axioms(policy, d)))
    if d["name"] in owned:
        return []
    return [P("rejected", "orphan_justification", {}, {"rule": "orphan_justification"})]


def rule_set_option(policy: Policy, options: list[dict], docstring: str | None,
                    file_rel: str) -> tuple[list[Effect], list[dict]]:
    """Opções sob o alcance da declaração (Etapa A). Proibida → Rejeitada (só nesta declaração,
    O-3), salvo isenção de heartbeat com as duas condições; não reconhecida → Não resolvida."""
    effects, warnings = [], []
    for o in options:
        opt, val = o.get("option"), o.get("value")
        if opt is None:
            effects.append(P("unresolved", "set_option_unrecognized", {"line": o.get("line")}))
            continue
        if (opt, val) in policy.forbidden_options:
            if _heartbeat_exempt(policy, o, docstring, file_rel):
                warnings.append({"code": "heartbeat_exemption_applied", "line": o.get("line")})
                continue
            v = {"rule": "set_option_violation", "option": opt, "value": val, "line": o.get("line")}
            effects.append(P("rejected", "set_option_violation", dict(v), v))
        elif not policy.option_recognized(opt):
            effects.append(P("unresolved", "set_option_unrecognized", {"option": opt, "line": o.get("line")}))
    return effects, warnings


def _heartbeat_exempt(policy: Policy, o: dict, docstring: str | None, file_rel: str) -> bool:
    if (o.get("option"), o.get("value")) != ("maxHeartbeats", "0") or o.get("scope") != "in":
        return False
    if not any(file_rel == p or file_rel.startswith(p.rstrip("/") + "/") for p in policy.exemption_paths):
        return False
    j = parse_justification(docstring)
    return j.status == "valid" and j.reason == policy.exemption_reason


def rule_anomalies(anomalies: list[dict]) -> list[Effect]:
    """Anomalias do inspetor: análise incompleta → os dois estados não resolvidos."""
    effects = []
    for a in anomalies:
        if a["code"] in ("inspector_disagreement", "missing_constants"):
            effects.append(P("unresolved", a["code"], a.get("detail") or {}))
            effects.append(M("unresolved", a["code"], a.get("detail") or {}))
    return effects


# --------------------------------------------------------------------------- consolidação

def consolidate(effects: list[Effect]) -> tuple[dict, dict]:
    def worst(state, order):
        sevs = [e.severity for e in effects if e.state == state]
        sev = next((s for s in order if s in sevs), None)
        reasons = [{"code": e.code, "detail": e.detail} for e in effects if e.state == state]
        return sev, reasons
    ps, pr = worst("proof", ("rejected", "unresolved"))
    ms, mr = worst("premises", ("nonconforming", "unresolved"))
    return {"value": PROOF[ps], "reasons": pr}, {"value": PREMISES[ms], "reasons": mr}


def overall(proof: str, premises: str) -> str:
    """Q4: rejected > unresolved > verified."""
    if proof == "Rejeitada" or premises == "Não conforme":
        return "rejected"
    if proof == "Não resolvida" or premises == "Não resolvido":
        return "unresolved"
    return "verified"


# --------------------------------------------------------------------------- avaliação

@dataclass
class Context:
    policy: Policy
    file_rel: str
    owner_docs: dict
    file_effects: list[Effect]          # valem para todas as declarações (Etapa A, set_option sem vínculo)
    options_by_decl: dict               # nome (Etapa B) → [opções sob alcance]
    heartbeat_bound: set                # nomes vinculados a `set_option maxHeartbeats 0 in`
    anomalies_by_decl: dict
    tcb_complete: bool


def evaluate_declaration(ctx: Context, d: dict) -> dict:
    pol = ctx.policy
    effects: list[Effect] = list(ctx.file_effects)
    adm_eff, admissions = rule_admissions(pol, d)
    ax_eff, axioms, warnings = rule_axioms(pol, d)
    so_eff, so_warn = rule_set_option(pol, ctx.options_by_decl.get(d["name"], []), d.get("docstring"),
                                      ctx.file_rel)
    effects += adm_eff + ax_eff + so_eff
    effects += rule_native_evaluation(pol, d, ctx.owner_docs)
    effects += rule_native_implementations(pol, d)
    effects += rule_orphan_justification(pol, d, d["name"] in ctx.heartbeat_bound)
    effects += rule_anomalies(ctx.anomalies_by_decl.get(d["name"], []))
    if not ctx.tcb_complete:
        effects.append(P("unresolved", "tcb_incomplete"))
    proof, premises = consolidate(effects)
    own = parse_justification(d.get("docstring"))
    return {
        "declaration_name": d["name"],
        "declaration_kind": d.get("kind"),
        "proof_status": proof,
        "premises_status": premises,
        "correspondence_status": CORRESPONDENCE,
        "overall_status": overall(proof["value"], premises["value"]),
        "axioms": axioms,
        "admissions": admissions,
        "policy_violations": [e.violation for e in effects if e.violation is not None],
        "justification": own.as_dict(),
        "depends_on": list(d.get("depends_on", [])),
        "warnings": warnings + so_warn,
    }


def unelaborated_declaration(name: str, kind: str | None, code: str, detail: dict | None = None) -> dict:
    """Declaração vista só pela Etapa A (alvo não compilou, infraestrutura falhou, ou nome
    não encontrado no ambiente): nunca positiva."""
    r = {"code": code, "detail": detail or {}}
    return {
        "declaration_name": name, "declaration_kind": kind,
        "proof_status": {"value": "Não resolvida", "reasons": [r]},
        "premises_status": {"value": "Não resolvido", "reasons": [r]},
        "correspondence_status": CORRESPONDENCE, "overall_status": "unresolved",
        "axioms": [], "admissions": [], "policy_violations": [], "justification": None,
        "depends_on": [], "warnings": [],
    }


def fill_depends_on_rejected(decls: list[dict]) -> None:
    """O-3 (i): a dependente mantém o próprio estado; a dependência rejeitada fica visível."""
    rejected = {d["declaration_name"] for d in decls if d["proof_status"]["value"] == "Rejeitada"}
    for d in decls:
        d["depends_on_rejected"] = sorted(n for n in d.pop("depends_on", []) if n in rejected)


# --------------------------------------------------------------------------- Etapa A → declarações

STAGE_A_INFRA = {"unreadable_input", "environment_unpinned", "allowlist_unavailable", "allowlist_stale"}


def stage_a_names(sa) -> dict[str, dict]:
    """Declarações nomeadas da Etapa A: nome → {keyword, line}."""
    out = {}
    for it in sa.declarations:
        n = it.detail.get("name")
        if n:
            out.setdefault(n, {"keyword": it.detail.get("keyword"), "line": it.line})
    return out


def options_in_reach(policy: Policy, sa, b_names: list[str]) -> tuple[dict, set, list[Effect]]:
    """Mapeia cada `set_option` da Etapa A às declarações da Etapa B sob seu alcance.

    * forma `in`: só a declaração vinculada (pelo nome; privadas pelo nome de usuário);
    * arquivo/seção: toda declaração que não esteja comprovadamente ANTES da opção
      (aproximação conservadora: o fim de seção não é rastreado; L-3).
    Opção `in` que não se vincula a declaração com nome, sendo proibida ou não reconhecida,
    não pode ser atribuída → efeito no arquivo inteiro (`set_option_unattributed`)."""
    a = stage_a_names(sa)
    by_user = {}
    for n in b_names:
        by_user.setdefault(user_name(n), []).append(n)
    reach: dict[str, list[dict]] = {n: [] for n in b_names}
    bound_hb, file_effects = set(), []
    for f in sa.findings:
        if f.code != "set_option":
            continue
        o = {**f.detail, "line": f.line}
        relevant = o.get("option") is None or (o["option"], o.get("value")) in policy.forbidden_options \
            or not policy.option_recognized(o["option"])
        if o.get("scope") == "in":
            targets = by_user.get(o.get("applies_to") or "", [])
            if not targets:
                if relevant:
                    file_effects.append(P("unresolved", "set_option_unattributed", {"line": f.line}))
                continue
            for t in targets:
                reach[t].append(o)
                if (o.get("option"), o.get("value")) == ("maxHeartbeats", "0"):
                    bound_hb.add(t)
        else:
            for n in b_names:
                line = a.get(user_name(n), {}).get("line")
                if line is None or line > f.line:
                    reach[n].append(o)
    return reach, bound_hb, file_effects


def stage_a_file_effects(sa) -> list[Effect]:
    content = [u for u in sa.unrecognized if u.code not in STAGE_A_INFRA]
    if not content:
        return []
    return [P("unresolved", "stage_a_unrecognized",
              {"items": [{"code": u.code, "line": u.line, **u.detail} for u in content]})]


def file_rel_path(target: Path, root: str | None) -> str:
    try:
        return Path(target).resolve().relative_to(Path(root).resolve()).as_posix() if root else Path(target).name
    except ValueError:
        return Path(target).name
