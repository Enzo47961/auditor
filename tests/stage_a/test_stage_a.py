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


def test_unlock_limits_in_is_recorded_as_the_three_options(proj):
    """D-41: `unlock_limits` (v4.36) zera `maxRecDepth`, `maxHeartbeats` e
    `synthInstance.maxHeartbeats`; a Etapa A o registra como os `set_option … 0` equivalentes."""
    r = run(proj, "unlock_limits in\n/-- doc -/\ntheorem t : True := trivial\n")
    assert [f.detail for f in r.findings] == [
        {"option": o, "value": "0", "via": "unlock_limits", "scope": "in", "applies_to": "t"}
        for o in ("maxRecDepth", "maxHeartbeats", "synthInstance.maxHeartbeats")]
    assert r.unrecognized == []


def test_unlock_limits_file_level_and_chained(proj):
    r = run(proj, "unlock_limits\ntheorem t : True := trivial\n")
    assert {(f.detail["scope"], f.detail["applies_to"]) for f in r.findings} == {("file_or_section", None)}
    r = run(proj, "set_option autoImplicit true in\nunlock_limits in\ntheorem u : True := trivial\n")
    assert {f.detail["applies_to"] for f in r.findings} == {"u"} and len(r.findings) == 4


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


# ------------------------------------------------------------------ D-56: `?` e `«$»`

@pytest.mark.parametrize("src", [
    "theorem t : True ∧ True := by\n  refine ⟨?_, ?_⟩ <;> trivial\n",
    "example : True := by\n  refine ?m\n  trivial\n",
    "theorem t (p : Prop) (h : p) : p ∧ True := ⟨?x.y, trivial⟩\n",
    "def f (x : Nat) : Nat := g $ x\n",
])
def test_question_mark_and_dollar_inside_terms_are_not_commands(proj, src):
    """(a) `?_`/`?m` são metavariáveis sintéticas e `$` é aplicação: não são o comando `?`/`«$»`."""
    r = run(proj, src)
    assert "syntax_extension_declared" not in codes(r.unrecognized), r.unrecognized


@pytest.mark.parametrize("src,command", [("? foo\n", "?"), ("$ x\n", "$")])   # «$» na allow-list = `$`
def test_symbol_command_at_column_zero_is_syntax_extension(proj, src, command):
    """(b) No início de comando, o comando-símbolo continua `syntax_extension_declared`."""
    r = run(proj, src)
    assert [(i.code, i.detail.get("command")) for i in r.unrecognized
            if i.code == "syntax_extension_declared"] == [("syntax_extension_declared", command)]
    assert "unknown_command" not in codes(r.unrecognized)


def test_indented_reserved_command_still_detected_anywhere(proj):
    """(c) Palavra reservada continua detectada em qualquer posição (L-2)."""
    r = run(proj, "section\n  macro \"x\" : term => `(1)\nend\nopen Foo in macro \"y\" : term => `(2)\n")
    assert [i.line for i in r.unrecognized if i.code == "syntax_extension_declared"] == [2, 4]


# ------------------------------------------------------------------ D-57: `module` de cabeçalho

def test_module_header_accepted_as_first_token(proj):
    r = run(proj, "/-\nCopyright\n-/\nmodule\n\npublic import Init.Core\nimport Init.Data\n\n"
                  "/-! doc do módulo -/\ntheorem t : True := trivial\n")
    assert r.unrecognized == []
    assert [d.detail["name"] for d in r.declarations] == ["t"]


def test_module_alone_is_a_valid_header(proj):
    assert run(proj, "module\n").unrecognized == []


@pytest.mark.parametrize("src,line", [
    ("import Init.Core\nmodule\n", 2),                       # depois de import
    ("theorem t : True := trivial\nmodule\n", 2),            # depois de comando
    ("module\nmodule\n", 2),                                 # duplicado
    ("/-! doc -/\nmodule\n", 2),                             # depois de docstring (é token)
])
def test_module_outside_first_position_is_unknown(proj, src, line):
    r = run(proj, src)
    assert [(i.code, i.detail.get("token"), i.line) for i in r.unrecognized] == \
        [("unknown_command", "module", line)]


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


# ------------------------------------------------------------------ Fase 1, P0-2 (a): continuações

@pytest.mark.parametrize("src", [
    "instance : Inhabited Nat :=\n{ default := 0 }\n",                    # Mathlib: `{ … with }` na coluna 0
    "theorem t : True ∧ True :=\n⟨trivial, trivial⟩\n",
    "def x : Nat :=\n(1 + 1)\n",
    "def l : List Nat :=\n[1, 2]\n",
    "def f (n : Nat) : Nat :=\nmatch n with\n| 0 => 0\n| _ => 1\n",
    "def g : Nat :=\nlet y := 1; y\n",
    "def h : Nat → Nat :=\nfun n => n\n",
    "def s (n : Nat) : String :=\nf!\"{n}\"\n",
    "def io : IO Unit :=\ndo\n  pure ()\n",
    "theorem u : True :=\nby trivial\n",
])
def test_term_continuations_at_column_zero_are_not_unknown(proj, src):
    """Termo continuado na coluna 0 não é comando (falso positivo medido no Mathlib, P0-2 a)."""
    assert run(proj, src).unrecognized == []


def test_continuations_are_never_command_tokens_in_the_pinned_core():
    """Nenhuma continuação é token inicial de comando do toolchain fixado (o gerador recusa; aqui
    a conferência é sobre o arquivo versionado)."""
    allow = A.load_allowlist(TOOLCHAIN)
    commands = set().union(*(allow[k] for k in A.COMMAND_KEYS))
    assert {"match", "let", "{", "(", "f!", "add_decl_doc"} <= allow["continuation"] | allow["doc_continuation"]
    assert not (allow["continuation"] | allow["doc_continuation"]) & commands


def test_check_continuations_refuses_a_command_token():
    from auditor.allowlist import AllowlistError, check_continuations
    check_continuations({"theorem", "«cmd%»"}, ["match"], ["add_decl_doc"])
    with pytest.raises(AllowlistError):
        check_continuations({"theorem", "match"}, ["match"], [])
    with pytest.raises(AllowlistError):
        check_continuations({"«add_decl_doc»"}, [], ["add_decl_doc"])


def test_continuation_that_is_a_command_in_the_environment_is_dropped():
    """Se o ambiente tem `calc` como comando, `calc` deixa de ser continuação (fail-closed)."""
    allow = {"allowed": set(), "syntax_extension": set(), "metaprogramming": {"calc"},
             "unclassified": set(), "continuation": {"|"}, "doc_continuation": set()}
    out = A._settle_continuations(allow, A.load_allowlist(TOOLCHAIN))
    assert "calc" not in out["continuation"] and "match" in out["continuation"] and "|" in out["continuation"]
    assert "add_decl_doc" in out["doc_continuation"]


def test_add_decl_doc_only_right_after_a_docstring(proj):
    """`docComment >> "add_decl_doc " >> ident` (Lean/Parser/Command.lean:939): sem a docstring
    `/--` logo antes, `add_decl_doc` na coluna 0 continua não reconhecido."""
    assert run(proj, "structure P where\n  x : Nat\n/-- doc -/\nadd_decl_doc P.x\n").unrecognized == []
    for src in ["add_decl_doc P.x\n", "/-! doc do módulo -/\nadd_decl_doc P.x\n",
                "/-- doc -/\ntheorem t : True := trivial\nadd_decl_doc t\n"]:
        assert [(i.code, i.detail.get("token")) for i in run(proj, src).unrecognized] == \
            [("unknown_command", "add_decl_doc")], src


def test_percent_command_at_column_zero_is_classified_not_unknown(proj):
    """`cmd%` é um token para o Lean: na coluna 0 sai pela classificação, não como desconhecido."""
    r = run(proj, "cbv_simproc_pattern% foo\n")
    assert codes(r.unrecognized) == ["metaprogramming_command"]


def test_continuation_does_not_hide_risky_commands(proj):
    r = run(proj, "def g : Nat :=\nlet y := 1; y\n#eval g\n(\n#eval g)\n")
    assert codes(r.unrecognized) == ["metaprogramming_command", "metaprogramming_command"]


@pytest.mark.parametrize("src", [
    "def k (x : Nat) : Nat := match x with\n  | 0 => 1\n  | _ => 2\nexample : Nat := k .abbrev\n",
    "def names : List Lean.Name := [`theorem, `lemma]\n",
    "def finsum (lemma := finsum_def') : Nat := 0\n",
    "structure U where\nattribute [class] U\n",
    "@[class, simp] structure S where\n",
])
def test_declaration_keyword_in_non_declaration_position(proj, src):
    """`.abbrev`, `` `lemma ``, `(lemma := …)`, `[class]`: não começam declaração (P0-2 a)."""
    r = run(proj, src)
    assert "declaration_name_unresolved" not in codes(r.unrecognized), r.unrecognized


def test_real_declaration_name_still_required(proj):
    r = run(proj, "theorem\n")
    assert codes(r.unrecognized) == ["declaration_name_unresolved"]
    r = run(proj, "axiom ax : False\nexample := (ax)\n")
    assert [f.detail.get("name") for f in r.findings if f.code == "axiom"] == ["ax"]


# ------------------------------------------------------------------ L-33 (a): execução na elaboração

@pytest.mark.parametrize("src,line", [
    ("theorem t : True := by\n  run_tac do (IO.println \"x\" : IO Unit)\n  trivial\n", 2),
    ("theorem t : True := by\n  first\n  | run_tac pure ()\n  | trivial\n", 3),
    ("open Lean in\ntheorem u : True := by_elab do\n  return mkConst ``True.intro\n", 2),
])
def test_code_execution_detected_anywhere(proj, src, line):
    """`run_tac`/`by_elab` executam código do usuário na elaboração: achado em qualquer posição."""
    r = run(proj, src)
    assert [(f.code, f.line) for f in r.findings if f.code == "elaboration_code_execution"] == \
        [("elaboration_code_execution", line)]


@pytest.mark.parametrize("src", [
    "-- run_tac do IO.println \"x\"\ntheorem t : True := trivial\n",
    "def s : String := \"by_elab\"\n",
    "def «run_tac» : Nat := 1\n",
])
def test_code_execution_not_in_comments_strings_or_quoted_names(proj, src):
    assert "elaboration_code_execution" not in codes(run(proj, src).findings)


def test_executes_code_inventory_cites_the_toolchain_source():
    assert set(A.EXECUTES_CODE) == {"run_tac", "by_elab"}
    assert all(v.startswith("Lean/") and ":" in v for v in A.EXECUTES_CODE.values())


@pytest.mark.parametrize("src,line", [
    ("unsafe def f : Nat := 0\n", 1),
    ("def g : Nat := unsafe (unsafeCast 0)\n", 1),
    ("theorem t : True := by\n  exact (unsafe trivial)\n", 2),
])
def test_unsafe_is_unrecognized_anywhere(proj, src, line):
    assert [(i.code, i.line) for i in run(proj, src).unrecognized if i.code == "unsafe_code"] == [("unsafe_code", line)]


def test_unsafe_in_comment_string_or_quoted_name_is_not_flagged(proj):
    r = run(proj, "-- unsafe\ndef s : String := \"unsafe\"\ndef «unsafe» : Nat := 0\n")
    assert "unsafe_code" not in codes(r.unrecognized)


def test_show_panel_widgets_is_fail_closed(proj):
    """L-33: avalia termos do arquivo (Lean/Widget/Commands.lean:70–75), como `#widget`."""
    assert "metaprogramming_command" in codes(run(proj, "show_panel_widgets [- w]\n").unrecognized)


def test_core_risk_classification_prevails_over_older_project_allowlist():
    """Allow-list de projeto gerada antes da reclassificação: o risco do core vale sobre ela."""
    allow = {"allowed": {"show_panel_widgets", "theorem"}, "syntax_extension": set(), "metaprogramming": set(),
             "unclassified": set(), "continuation": set(), "doc_continuation": set()}
    out = A._settle_continuations(allow, A.load_allowlist(TOOLCHAIN))
    assert "show_panel_widgets" in out["metaprogramming"] and "show_panel_widgets" not in out["allowed"]
    assert "theorem" in out["allowed"]
