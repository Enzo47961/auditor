"""Regressão por regra da política (componente 4: "cada regra tem teste de regressão próprio").

Fatos sintéticos no formato da Etapa B; nenhuma chamada ao Lean. Cada seção cobre uma regra
de `policy.toml` / `aggregator.py`. Mudança de regra exige auditoria por quem não é o autor."""
import dataclasses

import pytest

from auditor import aggregator as ag
from auditor.policy import load_policy, parse_justification
from conftest import DEFAULT_POLICY

POL = load_policy(DEFAULT_POLICY)
JUST = 'Doc.\nauditor_justified: reason="motivo" reviewer="@rev"'


def fact(name="t", axioms=(), refs=None, doc=None, ib=(), ext=(), deps=()):
    """`refs`: {axioma: [(referenciador, dona)]}; padrão: a própria declaração."""
    refs = refs or {a: [(name, name)] for a in axioms}
    return {"name": name, "kind": "theorem", "docstring": doc, "axioms_official": list(axioms),
            "axioms_closure": list(axioms), "missing": [], "depends_on": list(deps),
            "axiom_referrers": [{"axiom": a, "referrers": [{"name": r, "owner": o} for r, o in rs]}
                                for a, rs in refs.items()],
            "implemented_by": [{"name": n, "implementation": n + "Impl", "level": lv} for n, lv in ib],
            "extern": [{"name": n, "level": lv} for n, lv in ext]}


def ctx(owner_docs=None, options=None, hb=(), file_effects=(), anomalies=None, tcb=True, policy=POL,
        file_rel="Fixture/Target.lean"):
    return ag.Context(policy=policy, file_rel=file_rel, owner_docs=owner_docs or {},
                      file_effects=list(file_effects), options_by_decl=options or {},
                      heartbeat_bound=set(hb), anomalies_by_decl=anomalies or {}, tcb_complete=tcb)


def ev(d, **kw):
    r = ag.evaluate_declaration(ctx(**kw), d)
    return r["proof_status"]["value"], r["premises_status"]["value"], r["overall_status"], r


def codes(r, key):
    return {x["code"] for x in r[key]["reasons"]}


# ------------------------------------------------------------------ axiomas

def test_clean_declaration_verified():
    assert ev(fact())[:3] == ("Validada", "Conforme", "verified")


@pytest.mark.parametrize("ax", ["Classical.choice", "propext", "Quot.sound"])
def test_allowed_axioms(ax):
    assert ev(fact(axioms=[ax]))[:3] == ("Validada", "Conforme", "verified")


def test_admission_rejects_proof_only():
    p, m, o, r = ev(fact(axioms=["sorryAx"], refs={"sorryAx": [("d", "d_lemma")]}))
    assert (p, m, o) == ("Rejeitada", "Conforme", "rejected")
    assert r["admissions"] == [{"name": "sorryAx", "origins": ["d_lemma"]}]


def test_unknown_axiom_fail_closed():
    p, m, o, r = ev(fact(axioms=["minhaAxioma"]))
    assert (p, m, o) == ("Validada", "Não resolvido", "unresolved")
    assert codes(r, "premises_status") == {"unknown_axiom"}


def test_forbidden_axiom_nonconforming():
    pol = dataclasses.replace(POL, forbidden_axioms=frozenset({"badAx"}))
    p, m, o, r = ev(fact(axioms=["badAx"]), policy=pol)
    assert (p, m, o) == ("Validada", "Não conforme", "rejected")
    assert r["policy_violations"] == [{"rule": "forbidden_axiom", "axiom": "badAx"}]


def test_unknown_axiom_allow_with_warning():
    pol = dataclasses.replace(POL, unknown_axiom_action="allow_with_warning",
                              unknown_axiom_justification="documentado")
    p, m, o, r = ev(fact(axioms=["minhaAxioma"]), policy=pol)
    assert (p, m, o) == ("Validada", "Conforme", "verified")
    assert r["warnings"][0]["code"] == "unknown_axiom_allowed_with_warning"


# ------------------------------------------------------------------ avaliação nativa (O-1/B)

NATIVE = "Lean.ofReduceBool"


def test_native_unjustified():
    d = fact(axioms=[NATIVE], refs={NATIVE: [("t._proof_1", "t")]})
    p, m, o, r = ev(d, owner_docs={"t": {"docstring": None}})
    assert (p, m, o) == ("Validada", "Não conforme", "rejected")
    assert r["policy_violations"] == [{"rule": "native_decide_unjustified", "owner": "t"}]


def test_native_justified():
    d = fact(axioms=[NATIVE], refs={NATIVE: [("t._proof_1", "t")]}, doc=JUST)
    p, m, o, r = ev(d, owner_docs={"t": {"docstring": JUST}})
    assert (p, m, o) == ("Validada", "Conforme", "verified")
    assert r["justification"] == {"reason": "motivo", "reviewer": "@rev"}


def test_native_ofReduceNat_same_rule():
    d = fact(axioms=["Lean.ofReduceNat"], refs={"Lean.ofReduceNat": [("t._proof_1", "t")]})
    assert ev(d, owner_docs={"t": {"docstring": None}})[1] == "Não conforme"


def test_native_malformed():
    d = fact(axioms=[NATIVE], refs={NATIVE: [("t._proof_1", "t")]})
    _, m, _, r = ev(d, owner_docs={"t": {"docstring": 'auditor_justified: reason="x"'}})
    assert m == "Não conforme" and codes(r, "premises_status") == {"native_decide_justification_malformed"}


def test_native_consumer_attributed_to_owner():
    d = fact(name="c", axioms=[NATIVE], refs={NATIVE: [("o._proof_1", "o")]})
    _, m, _, r = ev(d, owner_docs={"o": {"docstring": None}})
    assert m == "Não conforme" and r["policy_violations"][0]["owner"] == "o"


@pytest.mark.parametrize("owner_docs", [{}, {"other": {"docstring": JUST}}])
def test_native_owner_unresolved(owner_docs):
    d = fact(axioms=[NATIVE], refs={NATIVE: [("_x", None)]})
    p, _, _, r = ev(d, owner_docs=owner_docs)
    assert p == "Não resolvida" and "native_decide_owner_unresolved" in codes(r, "proof_status")


# ------------------------------------------------------------------ gramática da justificativa (L-4)

@pytest.mark.parametrize("doc,status", [
    (None, "absent"), ("Só texto.", "absent"),
    ('auditor_justified: reason="a b" reviewer="@x-1"', "valid"),
    ('auditor_justified: reason="a" reviewer="@x"   ', "valid"),           # só espaço final
    ('  auditor_justified: reason="a" reviewer="@x"', "malformed"),        # espaço inicial
    ('auditor_justified: reason="" reviewer="@x"', "malformed"),           # reason vazio
    ('auditor_justified: reason="a\\"b" reviewer="@x"', "malformed"),      # escape
    ('auditor_justified: reason="a" reviewer="x"', "malformed"),           # sem @
    ('auditor_justified: reason="a"', "malformed"),                        # sem reviewer
    ('auditor_justified: reviewer="@x" reason="a"', "malformed"),          # ordem
    ('auditor_justified: reason="a" reviewer="@x" extra', "malformed"),
    ('auditor_justified: reason="a" reviewer="@x"\nauditor_justified: reason="b" reviewer="@x"', "malformed"),
    ('auditor_justified: reason="split\nover" reviewer="@x"', "malformed"),
])
def test_justification_grammar(doc, status):
    assert parse_justification(doc).status == status


# ------------------------------------------------------------------ implemented_by / extern (Q7-a)

@pytest.mark.parametrize("attr", ["implemented_by", "extern"])
def test_user_level_alone_is_candidate(attr):
    d = fact(**{"ib" if attr == "implemented_by" else "ext": [("g", "user")]})
    p, m, _, r = ev(d)
    assert (p, m) == ("Não resolvida", "Conforme") and codes(r, "proof_status") == {f"{attr}_candidate"}


@pytest.mark.parametrize("attr", ["implemented_by", "extern"])
def test_combined_pattern_rejected_even_if_justified(attr):
    d = fact(axioms=[NATIVE], refs={NATIVE: [("t._proof_1", "t")]}, doc=JUST,
             **{"ib" if attr == "implemented_by" else "ext": [("g", "user"), ("Nat.add", "tcb")]})
    p, m, _, r = ev(d, owner_docs={"t": {"docstring": JUST}})
    assert (p, m) == ("Rejeitada", "Conforme")
    assert r["policy_violations"] == [{"rule": f"{attr}_reaches_native_eval", "constants": ["g"]}]


def test_toolchain_level_never_triggers():
    d = fact(axioms=[NATIVE], refs={NATIVE: [("t._proof_1", "t")]}, doc=JUST,
             ib=[("Lean.Name.str", "tcb")], ext=[("Nat.add", "tcb")])
    assert ev(d, owner_docs={"t": {"docstring": JUST}})[:3] == ("Validada", "Conforme", "verified")


def test_unclassified_boundary_fails_closed():
    d = fact(ext=[("Nat.add", "unresolved")])
    p, _, _, r = ev(d)
    assert p == "Não resolvida" and "tcb_boundary_unresolved" in codes(r, "proof_status")


def test_attribute_not_in_policy_is_ignored_by_rule():
    pol = dataclasses.replace(POL, native_attributes=("implemented_by",))
    assert ev(fact(ext=[("h", "user")]), policy=pol)[0] == "Validada"


# ------------------------------------------------------------------ justificativa órfã (Q3b)

def test_orphan_justification_rejected():
    p, m, _, r = ev(fact(name="holder", doc=JUST))
    assert (p, m) == ("Rejeitada", "Conforme") and r["policy_violations"] == [{"rule": "orphan_justification"}]


def test_justification_on_consumer_is_orphan():
    d = fact(name="c", axioms=[NATIVE], refs={NATIVE: [("o._proof_1", "o")]}, doc=JUST)
    _, _, _, r = ev(d, owner_docs={"o": {"docstring": JUST}})
    assert "orphan_justification" in codes(r, "proof_status")


def test_heartbeat_bound_justification_is_not_orphan():
    doc = 'auditor_justified: reason="test-only heartbeat exemption" reviewer="@rev"'
    assert "orphan_justification" not in codes(ev(fact(doc=doc), hb={"t"})[3], "proof_status")


# ------------------------------------------------------------------ set_option (item 4, O-3)

def opt(option, value, scope="in", line=1):
    return {"option": option, "value": value, "scope": scope, "line": line}


@pytest.mark.parametrize("o,v", [("maxHeartbeats", "0"), ("autoImplicit", "true"),
                                 ("checkBinderAnnotations", "false"), ("debug.skipKernelTC", "true")])
def test_forbidden_option_rejects(o, v):
    p, _, _, r = ev(fact(), options={"t": [opt(o, v)]})
    assert p == "Rejeitada" and r["policy_violations"][0]["rule"] == "set_option_violation"


@pytest.mark.parametrize("o,v", [("maxHeartbeats", "400000"), ("autoImplicit", "false"),
                                 ("linter.unusedVariables", "false"), ("pp.all", "true")])
def test_allowed_option(o, v):
    assert ev(fact(), options={"t": [opt(o, v)]})[0] == "Validada"


def test_unrecognized_option_fails_closed():
    p, _, _, r = ev(fact(), options={"t": [opt("compiler.extract_closed", "false")]})
    assert p == "Não resolvida" and codes(r, "proof_status") == {"set_option_unrecognized"}


HB_DOC = 'auditor_justified: reason="test-only heartbeat exemption" reviewer="@rev"'


def test_heartbeat_exemption_default_policy_never_exempts():
    assert ev(fact(doc=HB_DOC), options={"t": [opt("maxHeartbeats", "0")]}, hb={"t"})[0] == "Rejeitada"


@pytest.mark.parametrize("path,doc,scope,expected", [
    ("tests/Heavy.lean", HB_DOC, "in", "Validada"),                     # (a) e (b): isento
    ("src/Heavy.lean", HB_DOC, "in", "Rejeitada"),                      # falta (a)
    ("tests/Heavy.lean", JUST, "in", "Rejeitada"),                      # falta (b): reason errado
    ("tests/Heavy.lean", None, "in", "Rejeitada"),                      # falta (b)
    ("tests/Heavy.lean", HB_DOC, "file_or_section", "Rejeitada"),       # nível de arquivo nunca
])
def test_heartbeat_exemption_needs_both_conditions(path, doc, scope, expected):
    pol = dataclasses.replace(POL, exemption_paths=("tests",))
    r = ev(fact(doc=doc), options={"t": [opt("maxHeartbeats", "0", scope)]}, hb={"t"},
           policy=pol, file_rel=path)
    assert r[0] == expected


# ------------------------------------------------------------------ fail-closed transversais

def test_file_effect_applies():
    p, _, _, r = ev(fact(), file_effects=[ag.P("unresolved", "stage_a_unrecognized")])
    assert p == "Não resolvida"


@pytest.mark.parametrize("code", ["inspector_disagreement", "missing_constants"])
def test_inspector_anomaly_unresolves_both(code):
    p, m, _, _ = ev(fact(), anomalies={"t": [{"declaration": "t", "code": code, "detail": {}}]})
    assert (p, m) == ("Não resolvida", "Não resolvido")


def test_incomplete_tcb_never_validated():
    p, _, _, r = ev(fact(), tcb=False)
    assert p == "Não resolvida" and codes(r, "proof_status") == {"tcb_incomplete"}


# ------------------------------------------------------------------ consolidação (Q4) e O-3

@pytest.mark.parametrize("proof,prem,expected", [
    ("Validada", "Conforme", "verified"), ("Validada", "Não conforme", "rejected"),
    ("Validada", "Não resolvido", "unresolved"), ("Rejeitada", "Conforme", "rejected"),
    ("Rejeitada", "Não conforme", "rejected"), ("Rejeitada", "Não resolvido", "rejected"),
    ("Não resolvida", "Conforme", "unresolved"), ("Não resolvida", "Não conforme", "rejected"),
    ("Não resolvida", "Não resolvido", "unresolved"),
])
def test_overall_table_q4(proof, prem, expected):
    assert ag.overall(proof, prem) == expected


def test_worst_wins_within_a_state():
    p, _, _, _ = ev(fact(axioms=["sorryAx"], ext=[("h", "user")]))
    assert p == "Rejeitada"      # Rejeitada (sorry) prevalece sobre Não resolvida (candidato)


def test_dependent_of_rejected_keeps_own_state():
    a = ag.evaluate_declaration(ctx(options={"a": [opt("maxHeartbeats", "0")]}), fact(name="a"))
    b = ag.evaluate_declaration(ctx(), fact(name="b", deps=["a"]))
    ag.fill_depends_on_rejected([a, b])
    assert a["proof_status"]["value"] == "Rejeitada"
    assert b["overall_status"] == "verified" and b["depends_on_rejected"] == ["a"]
