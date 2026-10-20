"""Testes unitários da Etapa A (varredura léxica)."""
import dataclasses
from pathlib import Path

import pytest

from conftest import CONFORMANCE, FAIL_CLOSED, ROOT
from auditor.tier1 import stage_a as A

TOOLCHAIN = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()


@pytest.fixture
def proj(tmp_path):
    (tmp_path / "lean-toolchain").write_text(TOOLCHAIN + "\n")
    return tmp_path


def run(proj: Path, src: str) -> A.StageAResult:
    f = proj / "T.lean"
    f.write_text(src, encoding="utf-8")
    return A.analyze(f)


def codes(items):
    return [i.code for i in items]


# ------------------------------------------------------------------ contrato

def test_result_has_no_positive_conclusion_field():
    fields = {f.name for f in dataclasses.fields(A.StageAResult)}
    assert fields == {"file", "toolchain", "allowlist", "stage_a_version", "findings",
                      "unrecognized", "warnings", "declarations"}


# ------------------------------------------------------------------ léxico

def test_sorry_in_comments_and_strings_is_not_a_candidate(proj):
    r = run(proj, '-- sorry\n/- sorry /- nested sorry -/ sorry -/\n'
                  'def s : String := "sorry \\" sorry"\ndef c : Char := \'s\'\n'
                  'def raw : String := r#"a "sorry" b"#\n')
    assert "sorry" not in codes(r.findings)
    assert r.unrecognized == []


def test_doc_comment_is_a_token_not_skipped(proj):
    r = run(proj, "/-- doc with sorry -/\ntheorem t : True := trivial\n")
    assert "sorry" not in codes(r.findings)
    assert [d.detail["name"] for d in r.declarations] == ["t"]


@pytest.mark.parametrize("src", ["/- open", 'def s := "open', "def «open : Nat := 1"])
def test_unterminated_is_lex_error(proj, src):
    assert codes(run(proj, src + "\n").unrecognized) == ["lex_error"]


def test_dotted_identifier_with_keyword_component_is_not_keyword(proj):
    r = run(proj, "theorem t : True := List.prefix.foo\n")
    assert r.unrecognized == []


def test_identifier_with_prime_is_not_char_literal(proj):
    r = run(proj, "theorem h' : True := by\n  have h'' : True := trivial\n  sorry\n")
    assert codes(r.findings) == ["sorry"]


# ------------------------------------------------------------------ candidatos

def test_candidates(proj):
    r = run(proj, "axiom ax : False\n"
                  "theorem a : 1 = 1 := by admit\n"
                  "theorem b : 1 < 2 := by native_decide\n"
                  "theorem c : 1 < 2 := by decide +native\n"
                  "@[implemented_by fImpl] def f : Nat := 0\n")
    assert codes(r.findings) == ["axiom", "admit", "native_decide", "native_decide", "implemented_by"]
    assert r.findings[0].detail["name"] == "ax"
    assert r.findings[3].detail["form"] == "+native"
    assert r.findings[4].detail["implementation"] == "fImpl"


def test_qualified_names(proj):
    r = run(proj, "namespace A.B\ntheorem t : True := trivial\nsection\n"
                  "theorem u : True := trivial\nend\nend A.B\ntheorem _root_.v : True := trivial\n"
                  "theorem w : True := trivial\n")
    assert [d.detail["name"] for d in r.declarations] == ["A.B.t", "A.B.u", "v", "w"]


# ------------------------------------------------------------------ set_option

def test_set_option_in_binds_to_next_declaration(proj):
    r = run(proj, "set_option maxHeartbeats 0 in\n/-- doc -/\n@[simp] private theorem t : True := trivial\n")
    so = r.findings[0]
    assert so.detail == {"option": "maxHeartbeats", "value": "0", "scope": "in", "applies_to": "t"}


def test_set_option_in_chained(proj):
    r = run(proj, "set_option maxHeartbeats 0 in\nset_option autoImplicit true in\ntheorem t : True := trivial\n")
    assert [f.detail["applies_to"] for f in r.findings] == ["t", "t"]


def test_set_option_in_before_non_declaration_binds_nothing(proj):
    r = run(proj, "set_option maxHeartbeats 0 in\nattribute [simp] foo\ntheorem t : True := trivial\n")
    assert r.findings[0].detail["applies_to"] is None


def test_set_option_file_level(proj):
    r = run(proj, "set_option maxHeartbeats 0\ntheorem t : True := trivial\n")
    assert r.findings[0].detail["scope"] == "file_or_section"
    assert r.findings[0].detail["applies_to"] is None


# ------------------------------------------------------------------ allow-list

@pytest.mark.parametrize("src,code", [
    ('macro "x" : term => `(1)\n', "syntax_extension_declared"),
    ('local notation "‖" x "‖" => x\n', "syntax_extension_declared"),
    ("run_cmd pure ()\n", "metaprogramming_command"),
    ("#eval 1\n", "metaprogramming_command"),
    ("#exit\n", "metaprogramming_command"),
    # D-1 (revisor): comandos que avaliam termos durante a elaboração
    ("#reduce 1 + 1\n", "metaprogramming_command"),
    ("#guard 1 + 1 == 2\n", "metaprogramming_command"),
    ("#widget w\n", "metaprogramming_command"),
    # Q8 (critério do revisor): pode executar código compilado antes da Etapa B
    ("#guard_expr 1 = 1\n", "metaprogramming_command"),
    ("#check_tactic True ~> True by skip\n", "metaprogramming_command"),
    ("#check_tactic_failure True by skip\n", "metaprogramming_command"),
])
def test_risky_commands(proj, src, code):
    assert code in codes(run(proj, src).unrecognized)


@pytest.mark.parametrize("src", ["#check 1\n", "#synth Inhabited Nat\n", "#check_simp 1 + 0 ~> 1\n"])
def test_q8_reviewed_safe_commands_allowed(proj, src):
    """Q8: revisados e mantidos permitidos (não executam código compilado; L-17)."""
    assert run(proj, src).unrecognized == []


def test_unknown_column_zero_command_fails_closed(proj):
    """`lemma` é comando do Mathlib, não do core: sem allow-list do Mathlib → fail-closed (L-2)."""
    r = run(proj, "lemma t : True := trivial\n")
    assert [(i.code, i.detail["token"]) for i in r.unrecognized] == [("unknown_command", "lemma")]


def test_continuation_tokens_allowed(proj):
    r = run(proj, "def f : Nat → Nat\n| 0 => 0\n| n+1 => n\n")
    assert r.unrecognized == []


def test_no_toolchain_is_unpinned(tmp_path):
    f = tmp_path / "T.lean"; f.write_text("theorem t : True := trivial\n")
    assert "environment_unpinned" in codes(A.analyze(f).unrecognized)


def test_unknown_toolchain_has_no_allowlist(tmp_path):
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v0.0.0-nonexistent\n")
    f = tmp_path / "T.lean"; f.write_text("theorem t : True := trivial\n")
    r = A.analyze(f)
    assert "allowlist_unavailable" in codes(r.unrecognized) and r.allowlist is None


# ------------------------------------------------------------------ unicode

@pytest.mark.parametrize("cp,cls", [(0x202E, "bidi"), (0x2066, "bidi"), (0x200B, "zero_width"),
                                    (0xFEFF, "zero_width")])
def test_forbidden_unicode_anywhere_including_comments(proj, cp, cls):
    r = run(proj, f"-- comentário {chr(cp)} aqui\ntheorem t : True := trivial\n")
    assert [(i.code, i.detail["class"]) for i in r.unrecognized] == [("forbidden_unicode", cls)]


def test_confusable_pair_warns_but_does_not_fail(proj):
    r = run(proj, "theorem hi : True := trivial\ntheorem hι : True := trivial\n")
    assert r.unrecognized == []
    assert [(w.code, w.detail["spellings"]) for w in r.warnings] == [("confusable_identifiers", ["hi", "hι"])]


def test_single_char_math_letters_do_not_warn(proj):
    r = run(proj, "theorem t (α : Type) (a : α) (ι : Type) (i : ι) : True := trivial\n")
    assert r.warnings == []


def test_quoted_identifier_with_ascii_skeleton_warns(proj):
    r = run(proj, "theorem «Nοt» : True := trivial\n")   # ο grego
    assert "confusable_quoted_identifier" in codes(r.warnings)


# ------------------------------------------------------------------ fixtures reais

def test_conformance_01_sorry_is_candidate():
    r = A.analyze(CONFORMANCE / "01-sorry-target" / "Fixture" / "Target.lean")
    assert codes(r.findings) == ["sorry"] and r.unrecognized == []


def test_conformance_02_transitive_sorry_is_invisible_to_stage_a():
    """L-2: a Etapa A só vê o texto do alvo. O sorry em D é trabalho da Etapa B."""
    r = A.analyze(CONFORMANCE / "02-sorry-transitive" / "Fixture" / "A.lean")
    assert r.findings == [] and r.unrecognized == []


@pytest.mark.parametrize("fixture,code", [("macro-custom", "syntax_extension_declared"),
                                          ("namespace-unicode", "forbidden_unicode")])
def test_fail_closed_fixtures_unrecognized(fixture, code):
    r = A.analyze(FAIL_CLOSED / fixture / "Fixture" / "Target.lean")
    assert code in codes(r.unrecognized)


def test_fail_closed_circular_is_invisible_to_stage_a():
    """Ciclo de imports é detectado na Etapa B (build), não aqui."""
    r = A.analyze(FAIL_CLOSED / "circular-dependency" / "Fixture" / "A.lean")
    assert r.unrecognized == []


def test_allowlist_content_must_match_its_toolchain(tmp_path, monkeypatch):
    """Arquivo de allow-list cujo conteúdo declara outro toolchain é rejeitado (fail-closed)."""
    import json
    real = json.loads(A.allowlist_path(TOOLCHAIN).read_text(encoding="utf-8"))
    (tmp_path / "allowlist").mkdir()
    tampered = {**real, "toolchain": "leanprover/lean4:v9.9.9"}
    (tmp_path / "allowlist" / A.allowlist_path(TOOLCHAIN).name).write_text(json.dumps(tampered))
    monkeypatch.setattr(A, "DATA", tmp_path)
    assert A.load_allowlist(TOOLCHAIN) is None
