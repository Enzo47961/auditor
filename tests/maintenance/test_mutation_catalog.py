"""O catálogo de mutações não pode apodrecer: todo padrão ocorre exatamente uma vez no arquivo,
toda mutação muda o código, e todo caminho de teste citado existe. Rápido (não roda mutações)."""
import importlib.util

import pytest

from conftest import ROOT

spec = importlib.util.spec_from_file_location("catalog", ROOT / "tools" / "mutation" / "catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)

CASES = [(g, rel, old, new) for g, d in catalog.GROUPS.items() for rel, old, new in d["mutations"]]


@pytest.mark.parametrize("group,rel,old,new", CASES, ids=[f"{c[0]}-{i}" for i, c in enumerate(CASES)])
def test_pattern_occurs_exactly_once_and_mutates(group, rel, old, new):
    text = (ROOT / rel).read_text(encoding="utf-8")
    assert text.count(old) == 1, f"padrão ausente ou ambíguo em {rel}: {old!r}"
    assert old != new


@pytest.mark.parametrize("group", sorted(catalog.GROUPS))
def test_group_test_paths_exist(group):
    for t in catalog.GROUPS[group]["tests"]:
        assert (ROOT / t).exists(), t
