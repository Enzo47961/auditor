"""Fronteira de TCB (Q7, opção a): testes unitários do algoritmo de docs/tcb.md.

Toolchain e manifest sintéticos (sem Lean): cada condição do algoritmo tem um caso."""
import json

import pytest

from auditor import tcb_boundary as tb


@pytest.fixture
def env(tmp_path):
    sysroot = tmp_path / "toolchain"
    lib = sysroot / "lib" / "lean"
    (lib / "Init").mkdir(parents=True)
    for m in ("Init.olean", "Init/Prelude.olean", "Lean.olean"):
        (lib / m).write_bytes(b"")
    proj = tmp_path / "proj"
    (proj / ".lake" / "build" / "lib" / "lean" / "Fixture").mkdir(parents=True)
    (proj / ".lake" / "build" / "lib" / "lean" / "Fixture" / "Dep.olean").write_bytes(b"")
    dep = proj / ".lake" / "packages" / "batteries" / ".lake" / "build" / "lib" / "lean" / "Batteries"
    dep.mkdir(parents=True)
    (dep / "Data.olean").write_bytes(b"")
    local = proj / "vendor" / "localdep" / ".lake" / "build" / "lib" / "lean"
    local.mkdir(parents=True)
    (local / "Local.olean").write_bytes(b"")
    manifest = {"version": "1.1.0", "packagesDir": ".lake/packages", "packages": [
        {"type": "git", "name": "batteries", "rev": "abc"},
        {"type": "path", "name": "localdep", "dir": "vendor/localdep"}]}
    (proj / "lake-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return proj, sysroot


def boundary(env):
    proj, sysroot = env
    return tb.load_boundary(proj, sysroot)


def test_toolchain_roots_are_declared_by_toolchain_files(env):
    assert boundary(env).toolchain_roots == {"Init", "Lean"}


def test_user_roots_come_from_manifest(env):
    b = boundary(env)
    assert b.packages == ("batteries", "localdep")
    assert len(b.user_roots) == 3       # projeto + 2 pacotes


def test_toolchain_module_is_tcb(env):
    _, sysroot = env
    olean = sysroot / "lib" / "lean" / "Init" / "Prelude.olean"
    assert tb.classify(boundary(env), "Init.Prelude", olean) == ("tcb", "toolchain_root")


@pytest.mark.parametrize("module,rel", [
    ("Fixture.Dep", ".lake/build/lib/lean/Fixture/Dep.olean"),                              # projeto
    ("Batteries.Data", ".lake/packages/batteries/.lake/build/lib/lean/Batteries/Data.olean"),  # git
    ("Local", "vendor/localdep/.lake/build/lib/lean/Local.olean"),                           # path
])
def test_user_modules_are_user(env, module, rel):
    proj, _ = env
    assert tb.classify(boundary(env), module, proj / rel) == ("user", "user_root")


def test_module_name_imitating_toolchain_in_user_package_is_user(env):
    """Um pacote do usuário com módulo chamado `Init.Fake` não vira TCB pelo nome."""
    proj, _ = env
    olean = proj / ".lake" / "build" / "lib" / "lean" / "Init" / "Fake.olean"
    olean.parent.mkdir(parents=True)
    olean.write_bytes(b"")
    assert tb.classify(boundary(env), "Init.Fake", olean)[0] == "user"


def test_root_not_declared_by_toolchain_is_unresolved(env):
    _, sysroot = env
    olean = sysroot / "lib" / "lean" / "Extra" / "Mod.olean"   # sem `Extra.olean` de 1º nível
    olean.parent.mkdir()
    olean.write_bytes(b"")
    assert tb.classify(boundary(env), "Extra.Mod", olean) == \
        ("unresolved", "module_root_not_declared_by_toolchain")


def test_path_not_matching_module_name_is_unresolved(env):
    _, sysroot = env
    olean = sysroot / "lib" / "lean" / "Init" / "Prelude.olean"
    assert tb.classify(boundary(env), "Init.Other", olean) == \
        ("unresolved", "olean_path_does_not_match_module")


def test_toolchain_module_shadowed_by_user_package_is_unresolved(env):
    proj, sysroot = env
    shadow = proj / ".lake" / "build" / "lib" / "lean" / "Init" / "Prelude.olean"
    shadow.parent.mkdir(parents=True)
    shadow.write_bytes(b"")
    olean = sysroot / "lib" / "lean" / "Init" / "Prelude.olean"
    assert tb.classify(boundary(env), "Init.Prelude", olean) == \
        ("unresolved", "module_shadowed_by_user_package")


@pytest.mark.parametrize("olean", [None, ""])
def test_missing_olean_is_unresolved(env, olean):
    assert tb.classify(boundary(env), "Init.Prelude", olean) == ("unresolved", "olean_not_found")


def test_olean_outside_every_declared_root_is_unresolved(env, tmp_path):
    stray = tmp_path / "elsewhere" / "Init" / "Prelude.olean"
    stray.parent.mkdir(parents=True)
    stray.write_bytes(b"")
    assert tb.classify(boundary(env), "Init.Prelude", stray) == \
        ("unresolved", "olean_outside_declared_roots")


def test_search_path_checked_against_manifest(env, tmp_path):
    proj, sysroot = env
    b = boundary(env)
    good = [str(sysroot / "lib" / "lean"), str(proj / ".lake" / "build" / "lib" / "lean")]
    assert tb.unrecognized_search_path(b, good) == []
    assert tb.unrecognized_search_path(b, good + [str(tmp_path)]) == [str(tmp_path)]


@pytest.mark.parametrize("manifest", [
    {"version": "2.0.0", "packages": []},
    {"version": "1.1.0", "packages": [{"type": "hg", "name": "x"}]},
    {"version": "1.1.0", "packages": [{"type": "path", "name": "x"}]},
    {"version": "1.1.0", "packages": [{"type": "git"}]},
])
def test_undeclarable_manifest_fails_closed(env, manifest):
    proj, sysroot = env
    (proj / "lake-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(tb.BoundaryError):
        tb.load_boundary(proj, sysroot)


def test_toolchain_without_roots_fails_closed(env, tmp_path):
    proj, _ = env
    empty = tmp_path / "empty"
    (empty / "lib" / "lean").mkdir(parents=True)
    with pytest.raises(tb.BoundaryError):
        tb.load_boundary(proj, empty)
