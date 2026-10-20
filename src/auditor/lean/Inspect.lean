import Lean
open Lean

/-! # Inspetor da Etapa B

Lê o ambiente elaborado (`.olean`) do módulo-alvo e emite FATOS BRUTOS em JSON.
Não aplica política, não decide estado, não emite selo: isso é do agregador (Python).

Uso: `inspect <Módulo> <saída.json>`, rodado sob `lake env` no projeto-alvo
(o `LEAN_PATH` vem do ambiente fixado do projeto).

Para cada declaração do módulo-alvo escrita no fonte:
* `axioms_official` — `Lean.collectAxioms`, o mesmo algoritmo de `#print axioms`;
* `axioms_closure`  — fecho de dependências calculado aqui, de forma independente,
  com o mesmo percurso; divergência entre os dois é exposta, não resolvida;
* `axiom_referrers` — para cada axioma, as constantes do fecho que o referenciam
  diretamente, e a declaração dona de cada uma (componentes internos removidos);
* `implemented_by`, `extern` — constantes do fecho com esses atributos;
* `missing` — constantes referenciadas que não existem no ambiente (o algoritmo
  oficial as ignora em silêncio);
* `docstring`, `depends_on` (outras declarações do alvo no fecho).
Também emite os metadados do fingerprint (`@[simp]`, `@[ext]`, `@[reducible]`,
`@[implemented_by]` de todo o ambiente importado). -/

def inspectorVersion : String := "1"

/-- Dependências diretas, espelhando `Lean.CollectAxioms.collect` (v4.22.0). -/
def directDeps (ci : ConstantInfo) : Array Name :=
  match ci with
  | .axiomInfo _    => #[]
  | .defnInfo v     => v.type.getUsedConstants ++ v.value.getUsedConstants
  | .thmInfo v      => v.type.getUsedConstants ++ v.value.getUsedConstants
  | .opaqueInfo v   => v.type.getUsedConstants ++ v.value.getUsedConstants
  | .quotInfo _     => #[]
  | .ctorInfo v     => v.type.getUsedConstants
  | .recInfo v      => v.type.getUsedConstants
  | .inductInfo v   => v.type.getUsedConstants ++ v.ctors.toArray

def kindOf : ConstantInfo → String
  | .axiomInfo _ => "axiom" | .defnInfo _ => "def" | .thmInfo _ => "theorem"
  | .opaqueInfo _ => "opaque" | .quotInfo _ => "quot" | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec" | .inductInfo _ => "inductive"

/-- Nome escrito pelo usuário? Nomes privados (`_private.<Mod>.0.foo`) são julgados
pela parte de usuário (`foo`); sem isso, toda declaração `private` pareceria interna. -/
def isUserFacing (n : Name) : Bool :=
  match privateToUserName? n with
  | some u => !u.isAnonymous && !u.isInternalDetail
  | none => !n.isInternalDetail

/-- Dona de uma constante auxiliar: remove componentes finais internos
(`foo._proof_1_3` → `foo`). Convenção do compilador; ver limitations.md (L-4). -/
partial def ownerOf (env : Environment) (n : Name) : Option Name :=
  if isUserFacing n then (if env.contains n then some n else none)
  else match n with
    | .str p _ => ownerOf env p
    | .num p _ => ownerOf env p
    | .anonymous => none

structure Ctx where
  env        : Environment
  sysrootLib : String
  deps       : IO.Ref (Std.HashMap Name (Array Name))
  toolchainMod : IO.Ref (Std.HashMap Nat Bool)

def Ctx.deps? (c : Ctx) (n : Name) : IO (Option (Array Name)) := do
  if let some d := (← c.deps.get)[n]? then return some d
  match c.env.find? n with
  | none => return none
  | some ci =>
    let d := directDeps ci
    c.deps.modify (·.insert n d)
    return some d

def Ctx.moduleOf (c : Ctx) (n : Name) : Option Name :=
  c.env.getModuleIdxFor? n |>.bind fun i => c.env.header.moduleNames[i.toNat]?

/-- A constante vem de um módulo do toolchain? Decidido pelo caminho do `.olean`
(sob `<sysroot>/lib/lean`), não pelo prefixo do nome do módulo. -/
def Ctx.inToolchain (c : Ctx) (n : Name) : IO Bool := do
  let some i := c.env.getModuleIdxFor? n | return false
  if let some b := (← c.toolchainMod.get)[i.toNat]? then return b
  let some m := c.env.header.moduleNames[i.toNat]? | return false
  let b ← try
      let p ← findOLean m
      let p ← IO.FS.realPath p
      pure (p.toString.startsWith c.sysrootLib)
    catch _ => pure false
  c.toolchainMod.modify (·.insert i.toNat b)
  return b

def nameJ (n : Name) : Json := toJson n.toString

def nameArr (ns : Array Name) : Json :=
  Json.arr ((ns.qsort (·.toString < ·.toString)).map nameJ)

/-- Declarações do alvo escritas no fonte: têm faixa de declaração e não são detalhe interno. -/
def targetDecls (env : Environment) (modIdx : ModuleIdx) : Array Name := Id.run do
  let mut out := #[]
  for n in env.header.moduleData[modIdx.toNat]!.constNames do
    if !isUserFacing n then continue
    if isAuxRecursor env n || isNoConfusion env n then continue
    if (declRangeExt.find? (level := .server) env n).isNone then continue
    out := out.push n
  return out.qsort (·.toString < ·.toString)

def inspectDecl (c : Ctx) (targets : NameSet) (n : Name) : IO Json := do
  let env := c.env
  let some ci := env.find? n | throw <| IO.userError s!"declaração sumiu do ambiente: {n}"
  -- fecho independente
  let mut visited : NameSet := {}
  let mut stack := #[n]
  let mut missing := #[]
  let mut axioms := #[]
  let mut referrers : Std.HashMap Name (Array Name) := {}
  while h : stack.size > 0 do
    let cur := stack.back
    stack := stack.pop
    if visited.contains cur then continue
    visited := visited.insert cur
    match ← c.deps? cur with
    | none => missing := missing.push cur
    | some ds =>
      if let some (.axiomInfo _) := env.find? cur then axioms := axioms.push cur
      for d in ds do
        if let some (.axiomInfo _) := env.find? d then
          referrers := referrers.insert d ((referrers.getD d #[]).push cur)
        unless visited.contains d do stack := stack.push d
  -- algoritmo oficial
  let official := (((CollectAxioms.collect n).run env).run {}).2.axioms
  let mut implBy := #[]
  let mut ext := #[]
  let mut dependsOn := #[]
  for m in visited.toArray do
    if let some impl := Compiler.implementedByAttr.getParam? env m then
      implBy := implBy.push <| Json.mkObj [("name", nameJ m), ("implementation", nameJ impl),
        ("module", toJson ((c.moduleOf m).map toString)), ("in_toolchain", toJson (← c.inToolchain m))]
    if isExtern env m then
      ext := ext.push <| Json.mkObj [("name", nameJ m),
        ("module", toJson ((c.moduleOf m).map toString)), ("in_toolchain", toJson (← c.inToolchain m))]
    if m != n && targets.contains m then dependsOn := dependsOn.push m
  let refJ := axioms.qsort (·.toString < ·.toString) |>.map fun ax =>
    let rs := (referrers.getD ax #[]).qsort (·.toString < ·.toString)
    Json.mkObj [("axiom", nameJ ax), ("referrers", Json.arr <| rs.map fun r =>
      Json.mkObj [("name", nameJ r), ("owner", toJson ((ownerOf env r).map toString))])]
  let doc ← findDocString? env n (includeBuiltin := false)
  return Json.mkObj [
    ("name", nameJ n),
    ("kind", toJson (kindOf ci)),
    ("type_hash", toJson (toString ci.type.hash)),
    ("value_hash", toJson ((ci.value? (allowOpaque := true)).map (toString ·.hash))),
    ("docstring", toJson doc),
    ("axioms_official", nameArr official),
    ("axioms_closure", nameArr axioms),
    ("axiom_referrers", Json.arr refJ),
    ("implemented_by", Json.arr implBy),
    ("extern", Json.arr ext),
    ("missing", nameArr missing),
    ("depends_on", nameArr dependsOn),
    ("closure_size", toJson visited.size)]

/-- Metadados do fingerprint: nomes ordenados de todo o ambiente importado. -/
def metadata (env : Environment) : Json := Id.run do
  let simp := Meta.simpExtension.getState env
  let mut simpNames : Array Name := simp.toUnfold.toList.toArray
  for o in simp.lemmaNames.toList do
    if let .decl d .. := o then simpNames := simpNames.push d
  let extNames := (Meta.Ext.extExtension.getState env).tree.values.map (·.declName)
  let mut red := #[]
  let mut impl := #[]
  for (n, _) in env.constants.toList do
    if getReducibilityStatusCore env n matches .reducible then red := red.push n
    if let some i := Compiler.implementedByAttr.getParam? env n then
      impl := impl.push (Name.mkStr n s!"→{i}")
  return Json.mkObj [
    ("simp", nameArr simpNames.toList.eraseDups.toArray), ("ext", nameArr extNames),
    ("reducible", nameArr red), ("implemented_by", nameArr impl)]

def main (args : List String) : IO UInt32 := do
  let [modStr, outPath] := args
    | IO.eprintln "uso: inspect <Módulo> <saída.json>"; return 2
  let sysroot ← findSysroot
  initSearchPath sysroot
  let mod := modStr.toName
  let env ← importModules #[{module := mod}] {} (loadExts := true)
  let some modIdx := env.getModuleIdx? mod
    | IO.eprintln s!"módulo não encontrado no ambiente: {mod}"; return 2
  let sysrootLib := (← IO.FS.realPath (sysroot / "lib" / "lean")).toString
  let c : Ctx := { env, sysrootLib, deps := ← IO.mkRef {}, toolchainMod := ← IO.mkRef {} }
  let decls := targetDecls env modIdx
  let targets := decls.foldl NameSet.insert {}
  let mut out := #[]
  for n in decls do
    out := out.push (← inspectDecl c targets n)
  let j := Json.mkObj [
    ("inspector_version", toJson inspectorVersion),
    ("lean_version", toJson Lean.versionString),
    ("lean_githash", toJson Lean.githash),
    ("module", toJson modStr),
    ("module_constant_count", toJson env.header.moduleData[modIdx.toNat]!.constNames.size),
    ("declarations", Json.arr out),
    ("metadata", metadata env)]
  IO.FS.writeFile outPath (j.compress ++ "\n")
  return 0
