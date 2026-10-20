"""Q5, camada 1: allow-list de projeto gerada contra um projeto Lake arbitrário.

O projeto mínimo (`mini-project/`) define um comando próprio (`my_lemma`), como o
Mathlib define `lemma`. Requisitos testados:
  * o gerador produz allow-list vinculada ao pino do ambiente;
  * a Etapa A a usa;
  * a Etapa A rejeita allow-list com pino errado (stale → fail-closed);
  * comando do projeto sem classificação explícita é fail-closed.
O `lean-toolchain` do projeto é escrito a partir da raiz (fonte única de verdade)."""
import json
import shutil

import pytest

from auditor import allowlist
from auditor.tier1 import stage_a
from conftest import ROOT, require_lake

MINI = ROOT / "tests" / "allowlist" / "mini-project"
TOOLCHAIN = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()


def codes(items, code):
    return [i for i in items if i.code == code]


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    require_lake()
    proj = tmp_path_factory.mktemp("gen") / "mini"
    shutil.copytree(MINI, proj)
    (proj / "lean-toolchain").write_text(TOOLCHAIN + "\n", encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 0
    return proj


@pytest.fixture
def proj(generated, tmp_path):
    """Cópia isolada do projeto já gerado, para testes que o alteram."""
    p = tmp_path / "mini"
    shutil.copytree(generated, p)
    return p


def read_allowlist(p):
    return json.loads((p / ".auditor" / "allowlist.json").read_text(encoding="utf-8"))


def test_generated_is_pinned_to_environment(generated):
    data = read_allowlist(generated)
    assert data["kind"] == "project"
    assert data["toolchain"] == TOOLCHAIN
    assert data["env_pin"] == allowlist.env_pin(
        TOOLCHAIN, (generated / "lake-manifest.json").read_bytes())
    assert data["unclassified"] == ["my_lemma"]
    assert "theorem" in data["allowed"] and "macro" in data["syntax_extension"]
    assert data["project_classification_sha256"] is None


def test_stage_a_uses_project_allowlist(generated):
    r = stage_a.analyze(generated / "Mini" / "Use.lean")
    assert r.allowlist["kind"] == "project"
    assert r.allowlist["env_pin"] == read_allowlist(generated)["env_pin"]


def test_unclassified_project_command_fails_closed(generated):
    r = stage_a.analyze(generated / "Mini" / "Use.lean")
    assert [i.detail["command"] for i in codes(r.unrecognized, "unclassified_command")] == ["my_lemma"]


def test_core_allowlist_alone_does_not_know_project_command(proj):
    (proj / ".auditor" / "allowlist.json").unlink()
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert r.allowlist["kind"] == "core"
    assert [i.detail["token"] for i in codes(r.unrecognized, "unknown_command")] == ["my_lemma"]


def test_classified_project_command_accepted(proj):
    cls = proj / ".auditor" / "classification.toml"
    cls.write_text('classification_version = "1"\nallowed = ["my_lemma"]\n', encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 0
    data = read_allowlist(proj)
    assert data["unclassified"] == [] and "my_lemma" in data["allowed"]
    assert data["project_classification_sha256"].startswith("sha256:")
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert r.unrecognized == []


@pytest.mark.parametrize("mutate", ["manifest", "toolchain_field", "env_pin_field", "kind_field"])
def test_stale_allowlist_fails_closed(proj, mutate):
    f = proj / ".auditor" / "allowlist.json"
    data = read_allowlist(proj)
    if mutate == "manifest":   # dependência mudou depois da geração
        m = proj / "lake-manifest.json"
        m.write_bytes(m.read_bytes().replace(b'"packages": []', b'"packages": [ ]'))
    elif mutate == "toolchain_field":
        data["toolchain"] = "leanprover/lean4:v0.0.0"
    elif mutate == "env_pin_field":
        data["env_pin"] = "sha256:" + "0" * 64
    else:
        data["kind"] = "core"
    if mutate != "manifest":
        f.write_text(json.dumps(data), encoding="utf-8")
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert codes(r.unrecognized, "allowlist_stale"), r.unrecognized
    assert r.allowlist is None


def test_explicit_missing_allowlist_fails_closed(generated, tmp_path):
    r = stage_a.analyze(generated / "Mini" / "Use.lean", allowlist_file=tmp_path / "nope.json")
    assert codes(r.unrecognized, "allowlist_stale")


def test_check_detects_drift(proj):
    assert allowlist.main(["--project", str(proj), "--check"]) == 0
    m = proj / "lake-manifest.json"
    m.write_bytes(m.read_bytes().replace(b'"packages": []', b'"packages": [ ]'))
    assert allowlist.main(["--project", str(proj), "--check"]) == 1


@pytest.mark.parametrize("toml", [
    'allowed = ["not_a_project_command"]\n',   # classificação apodrecida
    'allowed = ["theorem"]\n',                 # comando do core: não é do projeto
    'allowed = ["my_lemma"]\nmetaprogramming = ["my_lemma"]\n',
    'permitidos = ["my_lemma"]\n',             # chave desconhecida
])
def test_bad_classification_rejected(proj, toml):
    (proj / ".auditor" / "classification.toml").write_text(toml, encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 2


def test_unpinned_project_rejected(proj):
    (proj / "lake-manifest.json").unlink()
    assert allowlist.main(["--project", str(proj)]) == 2
