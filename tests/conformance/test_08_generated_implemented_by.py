"""Cenário 08 — `@[implemented_by]` gerado na elaboração (Fase 1, P0-1).

O fonte não escreve `implemented_by`; o Lean o gera (`T.ctorIdx`, `deriving TypeName`). A Etapa A
não o vê; a Etapa B vê. Este teste falha se um `implemented_by` gerado num módulo do projeto
chegar ao relatório como `verified` sem sinalização (docs/p0-1-implemented-by.md)."""
import pytest

from conftest import CONFORMANCE, assert_common_invariants, reasons, run_auditor, state
from auditor.tier1 import stage_a

TARGET = CONFORMANCE / "08-generated-implemented-by" / "Fixture" / "Target.lean"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return run_auditor(TARGET, tmp_path_factory.mktemp("r08"))


def candidates(d: dict) -> list[str]:
    return [c for r in d["proof_status"]["reasons"] if r["code"] == "implemented_by_candidate"
            for c in r["detail"]["constants"]]


def test_stage_a_does_not_see_generated_attribute():
    r = stage_a.analyze(TARGET)
    assert "implemented_by" not in [f.code for f in r.findings]
    assert r.unrecognized == []


@pytest.mark.parametrize("name", ["red_ne_green", "idx_red"])
def test_generated_ctor_idx_is_candidate(result, name):
    """`Color.ctorIdx` (gerado, `@[implemented_by Color.ctorIdx._impl]`): pelo `noConfusion` de
    `cases` e por uso direto."""
    assert_common_invariants(result)
    d = result.decl(name)
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    assert candidates(d) == ["Color.ctorIdx"]


@pytest.mark.parametrize("name", ["instTypeNameTag", "tag_name"])
def test_generated_type_name_instance_is_candidate(result, name):
    """`deriving TypeName`: `opaque inst` com nome higiênico e `@[implemented_by instImpl]`."""
    d = result.decl(name)
    assert state(d) == ("Não resolvida", "Conforme", "unresolved")
    assert [c.startswith("inst._@.Fixture.Target.") for c in candidates(d)] == [True]


@pytest.mark.parametrize("name", ["box_idx", "plain", "Color", "Box"])
def test_without_generated_attribute_is_verified(result, name):
    """Um construtor só (`Box.ctorIdx` é `macroInline`, sem atributo) e declarações que não
    chegam a nenhum `ctorIdx` com atributo saem `verified`: a sinalização não é indiscriminada."""
    assert state(result.decl(name)) == ("Validada", "Conforme", "verified")


def test_no_generated_candidate_is_ever_verified(result):
    for d in result.report["declarations"]:
        if candidates(d):
            assert d["overall_status"] != "verified", d["declaration_name"]
