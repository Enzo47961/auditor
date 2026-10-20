import Lake
open Lake DSL
package mini
@[default_target] lean_lib Mini where
  globs := #[.submodules `Mini]
