import Lean
open Lean

/-! # Inspetor da Etapa B

Lê o ambiente elaborado (`.olean`) do módulo-alvo e emite FATOS BRUTOS em JSON.
Não aplica política, não decide estado, não emite selo: isso é do agregador (Python).

Uso: `inspect <Módulo> <saída.json>`, rodado sob `lake env` no projeto-alvo
(o `LEAN_PATH` vem do ambiente fixado do projeto).

Para cada declaração do módulo-alvo escrita no fonte:
* `axioms_official` — `Lean.collectAxioms`, o código de `#print axioms`. Desde a v4.36 ele usa,
  para declarações importadas, axiomas pré-calculados gravados em cada `.olean`
  (`exportedAxiomsExt`). Sem `loadExts` essa extensão está vazia, e o algoritmo percorre os
  corpos de todas as constantes: o resultado não depende de resumo gravado no `.olean`;
* `axioms_closure`  — fecho de dependências calculado aqui, de forma independente, com o mesmo
  percurso; divergência entre os dois é exposta, não resolvida;
* `axiom_referrers` — para cada axioma, as constantes do fecho que o referenciam
  diretamente, e a declaração dona de cada uma (componentes internos removidos);
* `implemented_by`, `extern` — constantes do fecho com esses atributos, com o módulo e o
  caminho real do `.olean` de origem (a classificação TCB/usuário é do Python: Q7);
* `native_auxiliary` — axiomas do fecho com a FORMA de axioma auxiliar de avaliação nativa
  (v4.36: `native_decide`/`bv_decide` adicionam, por uso, um axioma `<dona>._native.<tática>.ax_…`
  com tipo `@Eq Bool e true`, `e` fechado; o kernel não o reconfere). Fato bruto: a forma não
  prova a origem — um `axiom` escrito à mão pode ter a mesma (Q9);
* `missing` — constantes referenciadas que não existem no ambiente (o algoritmo
  oficial as ignora em silêncio);
* `docstring`, `depends_on` (outras declarações do alvo no fecho).
No nível do arquivo, também `imports` (os módulos do fecho de imports) e `execution_capable` (as
constantes do módulo capazes de executar código na elaboração: tipo que alcança `IO.RealWorld`, ou
`@[extern]`), v5, L-33.
No nível do arquivo: `sysroot`, `search_path` (para conferência contra o manifest),
`owners` (docstring de toda declaração dona encontrada, inclusive fora do alvo).
Também emite os metadados do fingerprint (`@[simp]`, `@[ext]`, `@[reducible]`,
`@[implemented_by]` de todo o ambiente importado).

O ambiente é importado SEM carregar as extensões (`loadExts := false`): carregá-las exige
`enableInitializersExecution`, que executaria código dos módulos importados — inclusive do
PR auditado — dentro deste processo (D-39). Toda extensão é lida pelas entradas gravadas em
cada módulo (`getModuleEntries`), que a importação disponibiliza sem executar nada. -/

def inspectorVersion : String := "5"

/-- Dependências diretas, espelhando `Lean.CollectAxioms.collect` (v4.36.0-rc1: o tipo de um
axioma também é percorrido). -/
def directDeps (ci : ConstantInfo) : Array Name :=
  match ci with
  | .axiomInfo v    => v.type.getUsedConstants
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
  deps       : IO.Ref (Std.HashMap Name (Array Name))
  oleans     : IO.Ref (Std.HashMap Nat (Option String))

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

/-- Caminho real do `.olean` do módulo de origem da constante, resolvido pelo search path
efetivo (o mesmo que o `importModules` usou). Fato bruto: não decide TCB. -/
def Ctx.oleanOf (c : Ctx) (n : Name) : IO (Option String) := do
  let some i := c.env.getModuleIdxFor? n | return none
  if let some r := (← c.oleans.get)[i.toNat]? then return r
  let r ← match c.env.header.moduleNames[i.toNat]? with
    | none => pure none
    | some m => try pure (some (← IO.FS.realPath (← findOLean m)).toString) catch _ => pure none
  c.oleans.modify (·.insert i.toNat r)
  return r

def Ctx.originJ (c : Ctx) (m : Name) : IO (List (String × Json)) := do
  return [("module", toJson ((c.moduleOf m).map toString)), ("olean", toJson (← c.oleanOf m))]

def nameJ (n : Name) : Json := toJson n.toString

def nameArr (ns : Array Name) : Json :=
  Json.arr ((ns.qsort (·.toString < ·.toString)).map nameJ)

/-- Docstring como texto bruto (a gramática da justificativa é casada sobre ele). Docstring
Verso não tem texto bruto: vira `none`, e a justificativa conta como ausente (fail-closed). -/
def rawDocString? (env : Environment) (n : Name) : IO (Option String) := do
  match ← findInternalDocString? env n (includeBuiltin := false) with
  | some (.inl s) => return some s
  | _ => return none

/-- Tática de um axioma com a forma de auxiliar de avaliação nativa (`Lean.Meta.nativeEqTrue`,
v4.36.0-rc1): nome `p._native.<tática>.ax_…` e tipo `@Eq.{1} Bool e Bool.true`, `e` fechado. -/
def nativeAuxTactic? (ci : ConstantInfo) : Option Name :=
  match ci, ci.name with
  | .axiomInfo v, .str (.str (.str _ "_native") tac) last =>
    if !last.startsWith "ax_" then none else
    let t := v.type
    if t.isAppOfArity ``Eq 3 && t.getAppFn.constLevels! == [levelOne]
        && t.getArg! 0 == mkConst ``Bool && t.getArg! 2 == mkConst ``Bool.true then
      let e := t.getArg! 1
      if e.hasLooseBVars || e.hasFVar || e.hasMVar then none else some (.mkSimple tac)
    else none
  | _, _ => none

/-- L-33a: o TIPO alcança `IO.RealWorld` pelo fecho de dependências (definições incluídas)? Toda
mônada de meta-programação do Lean (`CoreM`, `MetaM`, `TermElabM`, `TacticM`, `CommandElabM`) é
construída sobre `EIO`, isto é, sobre `IO.RealWorld`: uma constante com esse tipo é código que, se o
elaborador a executar, tem acesso a IO. Memo negativo compartilhado entre as constantes do módulo. -/
def typeReachesWorld (c : Ctx) (noWorld : IO.Ref NameSet) (ty : Expr) : IO Bool := do
  let mut stack := ty.getUsedConstants
  let mut seen : NameSet := {}
  let mut order : Array Name := #[]
  while h : stack.size > 0 do
    let cur := stack.back
    stack := stack.pop
    if cur == ``IO.RealWorld then return true
    if seen.contains cur || (← noWorld.get).contains cur then continue
    seen := seen.insert cur
    order := order.push cur
    if let some ds ← c.deps? cur then
      for d in ds do stack := stack.push d
  noWorld.modify fun s => order.foldl (·.insert ·) s
  return false

/-- L-33a: constantes do módulo-alvo (todas, inclusive as geradas) capazes de executar código na
elaboração: tipo que alcança `IO.RealWorld` (elaborador, tática, simproc, handler de atributo,
procedimento de `initialize`…) ou `@[extern]`. Fato bruto; a decisão é do agregador. -/
def executionCapable (c : Ctx) (modIdx : ModuleIdx) : IO Json := do
  let noWorld ← IO.mkRef {}
  let mut out := #[]
  for n in c.env.header.moduleData[modIdx.toNat]!.constNames do
    let some ci := c.env.find? n | continue
    if isExtern c.env n then
      out := out.push <| Json.mkObj [("name", nameJ n), ("reason", toJson "extern")]
    else if ← typeReachesWorld c noWorld ci.type then
      out := out.push <| Json.mkObj [("name", nameJ n), ("reason", toJson "io_type")]
  return Json.arr (out.qsort (·.compress < ·.compress))

/-- Declarações do alvo escritas no fonte: têm faixa de declaração e não são detalhe interno. -/
def targetDecls (env : Environment) (modIdx : ModuleIdx) : Array Name := Id.run do
  let mut out := #[]
  for n in env.header.moduleData[modIdx.toNat]!.constNames do
    if !isUserFacing n then continue
    if isAuxRecursor env n || isNoConfusion env n then continue
    if (declRangeExt.find? (level := .server) env n).isNone then continue
    out := out.push n
  return out.qsort (·.toString < ·.toString)

def inspectDecl (c : Ctx) (targets : NameSet) (n : Name) : IO (Json × Array Name) := do
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
  let (official, _) ← (collectAxioms n : CoreM (Array Name)).toIO
    { fileName := "<inspect>", fileMap := default } { env }
  let mut implBy := #[]
  let mut ext := #[]
  let mut dependsOn := #[]
  for m in visited.toArray do
    if let some impl := Compiler.implementedByAttr.getParam? env m then
      implBy := implBy.push <| Json.mkObj
        ([("name", nameJ m), ("implementation", nameJ impl)] ++ (← c.originJ m))
    if isExtern env m then
      ext := ext.push <| Json.mkObj ([("name", nameJ m)] ++ (← c.originJ m))
    if m != n && targets.contains m then dependsOn := dependsOn.push m
  let refJ := axioms.qsort (·.toString < ·.toString) |>.map fun ax =>
    let rs := (referrers.getD ax #[]).qsort (·.toString < ·.toString)
    Json.mkObj [("axiom", nameJ ax), ("referrers", Json.arr <| rs.map fun r =>
      Json.mkObj [("name", nameJ r), ("owner", toJson ((ownerOf env r).map toString))])]
  let owners := axioms.foldl (init := #[]) fun acc ax =>
    (referrers.getD ax #[]).foldl (init := acc) fun acc r =>
      match ownerOf env r with | some o => acc.push o | none => acc
  let doc ← rawDocString? env n
  let nativeAux := axioms.qsort (·.toString < ·.toString) |>.filterMap fun ax =>
    (env.find? ax).bind nativeAuxTactic? |>.map fun tac =>
      Json.mkObj [("axiom", nameJ ax), ("tactic", nameJ tac),
                  ("owner", toJson ((ownerOf env ax).map toString))]
  return (·, owners) <| Json.mkObj [
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
    ("native_auxiliary", Json.arr nativeAux),
    ("missing", nameArr missing),
    ("depends_on", nameArr dependsOn),
    ("closure_size", toJson visited.size)]

/-- Metadados do fingerprint: nomes ordenados de todo o ambiente importado. `@[simp]` e
`@[ext]` vêm das entradas globais gravadas nos módulos (sem `loadExts`). -/
def metadata (env : Environment) : Json := Id.run do
  let mut simpNames : Array Name := #[]
  let mut extNames : Array Name := #[]
  for i in Array.range env.header.moduleNames.size do
    for e in Meta.simpExtension.ext.getModuleEntries env i do
      if let .global se := e then
        match se with
        | .thm t => if let .decl d .. := t.origin then simpNames := simpNames.push d
        | .toUnfold d => simpNames := simpNames.push d
        | .toUnfoldThms d _ => simpNames := simpNames.push d
    for e in Meta.Ext.extExtension.ext.getModuleEntries env i do
      if let .global t := e then extNames := extNames.push t.declName
  let mut red := #[]
  let mut impl := #[]
  for (n, _) in env.constants.toList do
    if getReducibilityStatusCore env n matches .reducible then red := red.push n
    if let some i := Compiler.implementedByAttr.getParam? env n then
      impl := impl.push (Name.mkStr n s!"→{i}")
  return Json.mkObj [
    ("simp", nameArr simpNames.toList.eraseDups.toArray), ("ext", nameArr extNames.toList.eraseDups.toArray),
    ("reducible", nameArr red), ("implemented_by", nameArr impl)]

def main (args : List String) : IO UInt32 := do
  let [modStr, outPath] := args
    | IO.eprintln "uso: inspect <Módulo> <saída.json>"; return 2
  let sysroot ← findSysroot
  initSearchPath sysroot
  let mod := modStr.toName
  let env ← importModules #[{module := mod}] {} (loadExts := false)
  let some modIdx := env.getModuleIdx? mod
    | IO.eprintln s!"módulo não encontrado no ambiente: {mod}"; return 2
  let c : Ctx := { env, deps := ← IO.mkRef {}, oleans := ← IO.mkRef {} }
  let decls := targetDecls env modIdx
  let targets := decls.foldl NameSet.insert {}
  let mut out := #[]
  let mut owners : NameSet := {}
  for n in decls do
    let (j, os) ← inspectDecl c targets n
    out := out.push j
    owners := os.foldl NameSet.insert owners
  let mut ownersJ := #[]
  for o in owners.toArray.qsort (·.toString < ·.toString) do
    ownersJ := ownersJ.push <| Json.mkObj [("name", nameJ o),
      ("docstring", toJson (← rawDocString? env o)),
      ("module", toJson ((c.moduleOf o).map toString))]
  let sp ← searchPathRef.get
  let j := Json.mkObj [
    ("inspector_version", toJson inspectorVersion),
    ("lean_version", toJson Lean.versionString),
    ("lean_githash", toJson Lean.githash),
    ("sysroot", toJson (← IO.FS.realPath sysroot).toString),
    ("search_path", toJson (sp.map (·.toString))),
    ("module", toJson modStr),
    ("module_constant_count", toJson env.header.moduleData[modIdx.toNat]!.constNames.size),
    -- módulos importados (fecho), para cruzar com os arquivos alterados do PR (L-33, dependência)
    ("imports", toJson ((env.header.moduleNames.filter (· != mod)).map toString)),
    ("execution_capable", ← executionCapable c modIdx),
    ("declarations", Json.arr out),
    ("owners", Json.arr ownersJ),
    ("metadata", metadata env)]
  IO.FS.writeFile outPath (j.compress ++ "\n")
  return 0
