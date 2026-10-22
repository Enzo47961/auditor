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
from conftest import ROOT, require_lake, run_auditor

MINI = ROOT / "tests" / "allowlist" / "mini-project"
# declaração de revisão obrigatória em toda classificação de projeto (L-26)
REVIEW = 'reviewed_by = "author-self-review"\nreviewer_independence = "none"\n'
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
    assert data["classification_review"] is None


def test_stage_a_uses_project_allowlist(generated):
    r = stage_a.analyze(generated / "Mini" / "Use.lean")
    assert r.allowlist["kind"] == "project"
    assert r.allowlist["env_pin"] == read_allowlist(generated)["env_pin"]
    assert r.allowlist["classification_review_status"] == "no-project-classification"


def test_unclassified_project_command_fails_closed(generated):
    r = stage_a.analyze(generated / "Mini" / "Use.lean")
    assert [i.detail["command"] for i in codes(r.unrecognized, "unclassified_command")] == ["my_lemma"]


def test_core_allowlist_alone_does_not_know_project_command(proj):
    (proj / ".auditor" / "allowlist.json").unlink()
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert r.allowlist["kind"] == "core"
    assert r.allowlist["classification_review_status"] == "core-only"
    assert [i.detail["token"] for i in codes(r.unrecognized, "unknown_command")] == ["my_lemma"]


def test_classified_project_command_accepted(proj):
    cls = proj / ".auditor" / "classification.toml"
    cls.write_text('classification_version = "1"\n' + REVIEW + 'revision_note = "teste"\n'
                   'allowed = ["my_lemma"]\n', encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 0
    data = read_allowlist(proj)
    assert data["unclassified"] == [] and "my_lemma" in data["allowed"]
    assert data["project_classification_sha256"].startswith("sha256:")
    assert data["classification_review"] == {"reviewed_by": "author-self-review",
                                             "reviewer_independence": "none", "revision_note": "teste"}
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert r.unrecognized == []
    assert r.allowlist["classification_review_status"] == "author-self-review"


def test_report_declares_classification_review_status(proj, tmp_path):
    """L-26: o relatório repete, no bloco `tcb`, quem revisou a classificação em uso."""
    (proj / ".auditor" / "classification.toml").write_text(
        REVIEW + 'allowed = ["my_lemma"]\n', encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 0
    r = run_auditor(proj / "Mini" / "Use.lean", tmp_path)
    assert r.report["tcb"]["classification_review_status"] == "author-self-review"
    assert all(d["tcb"]["classification_review_status"] == "author-self-review"
               for d in r.report["declarations"])
    assert r.exit_code == 0


@pytest.mark.parametrize("allow, status", [
    ({"kind": "core"}, "core-only"),
    ({"kind": "project"}, "no-project-classification"),
    ({"kind": "project", "project_classification_sha256": "sha256:x"}, "undeclared"),
    ({"kind": "project", "project_classification_sha256": "sha256:x",
      "classification_review": {"reviewed_by": None}}, "undeclared"),
    ({"kind": "project", "project_classification_sha256": "sha256:x",
      "classification_review": {"reviewed_by": "human-reviewed"}}, "human-reviewed"),
    ({"kind": "project", "project_classification_sha256": "sha256:x",
      "classification_review": {"reviewed_by": "independent-ai-reviewed"}}, "independent-ai-reviewed"),
])
def test_classification_review_status_values(allow, status):
    """L-26: o status vem da declaração; sem ela, `undeclared` (nunca um valor presumido).
    Mutação sobrevivente no run 39694466059: constante `author-self-review` passava."""
    assert stage_a.classification_review_status(allow) == status


def test_classification_hash_ignores_crlf(proj):
    """D-53 também no SHA-256 da classificação: o mesmo arquivo em CRLF e LF dá o mesmo hash."""
    cls = proj / ".auditor" / "classification.toml"
    text = REVIEW + 'allowed = ["my_lemma"]\n'
    cls.write_bytes(text.encode("utf-8"))
    assert allowlist.main(["--project", str(proj)]) == 0
    h_lf = read_allowlist(proj)["project_classification_sha256"]
    cls.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert allowlist.main(["--project", str(proj), "--check"]) == 0
    assert read_allowlist(proj)["project_classification_sha256"] == h_lf


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
    REVIEW + 'allowed = ["not_a_project_command"]\n',   # classificação apodrecida
    REVIEW + 'allowed = ["theorem"]\n',                 # comando do core: não é do projeto
    REVIEW + 'allowed = ["my_lemma"]\nmetaprogramming = ["my_lemma"]\n',
    REVIEW + 'permitidos = ["my_lemma"]\n',             # chave desconhecida
    # L-26: declaração de revisão obrigatória e coerente
    'allowed = ["my_lemma"]\n',                                              # sem reviewed_by
    'reviewed_by = "revisado"\nreviewer_independence = "none"\nallowed = ["my_lemma"]\n',
    'reviewed_by = "author-self-review"\nallowed = ["my_lemma"]\n',         # sem independência
    'reviewed_by = "author-self-review"\nreviewer_independence = "independent"\nallowed = ["my_lemma"]\n',
    'reviewed_by = "human-reviewed"\nreviewer_independence = "none"\nallowed = ["my_lemma"]\n',
    REVIEW + 'revision_note = 1\nallowed = ["my_lemma"]\n',
])
def test_bad_classification_rejected(proj, toml):
    (proj / ".auditor" / "classification.toml").write_text(toml, encoding="utf-8")
    assert allowlist.main(["--project", str(proj)]) == 2


def test_unpinned_project_rejected(proj):
    (proj / "lake-manifest.json").unlink()
    assert allowlist.main(["--project", str(proj)]) == 2


# --- D-53: fim de linha não muda o pino --------------------------------------------------------

def test_env_pin_ignores_crlf():
    lf = b'{"version": "1.1.0",\n "packages": []}\n'
    crlf = lf.replace(b"\n", b"\r\n")
    assert allowlist.env_pin(TOOLCHAIN, lf) == allowlist.env_pin(TOOLCHAIN, crlf)
    assert allowlist.env_pin(TOOLCHAIN, lf) != allowlist.env_pin(TOOLCHAIN, lf.replace(b"[]", b"[ ]"))


@pytest.mark.parametrize("eol", [b"\r\n", b"\n"])
def test_allowlist_survives_line_ending_change(proj, eol):
    """Allow-list gerada num clone LF vale num clone CRLF do mesmo commit, e vice-versa."""
    m = proj / "lake-manifest.json"
    lf = m.read_bytes().replace(b"\r\n", b"\n")
    m.write_bytes(lf.replace(b"\n", eol))
    assert allowlist.main(["--project", str(proj)]) == 0
    m.write_bytes(lf.replace(b"\n", b"\r\n" if eol == b"\n" else b"\n"))
    r = stage_a.analyze(proj / "Mini" / "Use.lean")
    assert r.allowlist is not None and r.allowlist["kind"] == "project", r.unrecognized
    assert allowlist.main(["--project", str(proj), "--check"]) == 0


# --- D-52: só as bibliotecas-alvo --------------------------------------------------------------

@pytest.mark.parametrize("lakefile,expected", [
    ("@[default_target] lean_lib Mini where\nlean_lib Tool\n", ["Mini"]),
    ("lean_lib Tool\n@[default_target]\nlean_lib «Mini» where\n", ["Mini"]),
    ("@[default_target] lean_lib A\n@[default_target] lean_lib B\n@[default_target] lean_exe c\n", ["A", "B"]),
])
def test_target_libs_from_lakefile_lean(tmp_path, lakefile, expected):
    (tmp_path / "lakefile.lean").write_text("import Lake\nopen Lake DSL\npackage p\n" + lakefile, encoding="utf-8")
    assert allowlist.target_libs(tmp_path) == expected


def test_target_libs_from_lakefile_toml(tmp_path):
    (tmp_path / "lakefile.toml").write_text(
        'name = "p"\ndefaultTargets = ["Mini", "app"]\n[[lean_lib]]\nname = "Mini"\n'
        '[[lean_lib]]\nname = "Tool"\n[[lean_exe]]\nname = "app"\n', encoding="utf-8")
    assert allowlist.target_libs(tmp_path) == ["Mini"]


def test_no_default_target_fails_closed(tmp_path):
    (tmp_path / "lakefile.lean").write_text("import Lake\nopen Lake DSL\npackage p\nlean_lib Mini\n",
                                            encoding="utf-8")
    with pytest.raises(allowlist.AllowlistError, match="--lib"):
        allowlist.target_libs(tmp_path)


def test_extraction_ignores_non_target_library(proj):
    """Duas lean_lib definem o mesmo nome (no Mathlib: `Mathlib` e `Cache`, ambas com
    `Lean.Name.fromComponents`). As duas não podem ser importadas juntas; a extração usa só a alvo."""
    (proj / "Mini" / "Clash.lean").write_text("def Lean.Name.clashAux : Nat := 0\n", encoding="utf-8")
    (proj / "Tool").mkdir()
    (proj / "Tool" / "Clash.lean").write_text("def Lean.Name.clashAux : Nat := 1\n", encoding="utf-8")
    with open(proj / "lakefile.lean", "a", encoding="utf-8") as f:
        f.write("\nlean_lib Tool where\n  globs := #[.submodules `Tool]\n")
    lake = require_lake()
    import subprocess
    b = subprocess.run([lake, "build", "Tool"], cwd=proj, capture_output=True, text=True, encoding="utf-8")
    assert b.returncode == 0, b.stdout + b.stderr
    assert (proj / ".lake" / "build" / "lib" / "lean" / "Tool" / "Clash.olean").is_file()

    assert allowlist.main(["--project", str(proj)]) == 0
    data = read_allowlist(proj)
    assert data["libraries"] == ["Mini"]
    assert data["module_count"] == 3          # Mini.Clash, Mini.Cmd, Mini.Use
    assert data["unclassified"] == ["my_lemma"]
    # a colisão é real: com as duas bibliotecas, o extrator falha (fail-closed, exit 2)
    assert allowlist.main(["--project", str(proj), "--lib", "Mini", "--lib", "Tool"]) == 2
