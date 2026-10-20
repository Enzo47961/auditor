import Lake
open Lake DSL
package fixture
-- precompileModules: o interpretador precisa do código nativo de `Fixture.Dep`
-- para avaliar o `@[extern]` durante a elaboração do `native_decide`.
@[default_target] lean_lib Fixture where
  globs := #[.submodules `Fixture]
  precompileModules := true
