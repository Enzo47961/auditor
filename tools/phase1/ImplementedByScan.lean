import Lean
open Lean

/-! # Medição de `@[implemented_by]`/`@[extern]` num projeto inteiro (Fase 1, P0-1)

Ferramenta de medição, não parte do auditor. Roda sob `lake env` no projeto-alvo, como o
inspetor, e importa o ambiente SEM extensões (`loadExts := false`, D-39): nada do projeto é
executado. Dois modos:

* `dump <Raiz> <saída.json>` — toda constante do ambiente com `@[implemented_by]` ou
  `@[extern]`: nome, implementação, módulo e caminho real do `.olean` (para a classificação
  TCB/usuário do próprio auditor, `tcb_boundary.classify`), faixa de declaração e a forma
  estrutural do `ctorIdx` gerado pelo Lean (`Lean/Meta/Constructions/CtorIdx.lean`, v4.36.0-rc1):
  `T.ctorIdx` com `@[implemented_by T.ctorIdx._impl]`, `_impl` `unsafe` cujo corpo é
  `getObjTagNat` aplicado. Também conta as declarações reportáveis dos módulos da raiz (o mesmo
  critério de `targetDecls` do inspetor).
* `reach <Raiz> <sementes.json> <saída.json>` — `sementes.json` = `{"categories": [...],
  "seeds": {nome: índice}}`. Para cada declaração reportável dos módulos da raiz, a máscara das
  categorias de semente alcançáveis no seu fecho, com o MESMO percurso de dependências do
  inspetor (`directDeps`: tipo e valor; a implementação de `implemented_by` não é percorrida).
  Calculado por busca no grafo reverso a partir das sementes.
-/

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

def isUserFacing (n : Name) : Bool :=
  match privateToUserName? n with
  | some u => !u.isAnonymous && !u.isInternalDetail
  | none => !n.isInternalDetail

def moduleOf (env : Environment) (n : Name) : Option Name :=
  env.getModuleIdxFor? n |>.bind fun i => env.header.moduleNames[i.toNat]?

def inRoot (root m : Name) : Bool := root.isPrefixOf m

/-- Declarações reportáveis de um módulo: o critério de `targetDecls` do inspetor. -/
def reportable (env : Environment) (n : Name) : Bool :=
  isUserFacing n && !isAuxRecursor env n && !isNoConfusion env n &&
    (declRangeExt.find? (level := .server) env n).isSome

partial def stripLams : Expr → Expr
  | .lam _ _ b _ => stripLams b
  | e => e

/-- Cabeça do corpo da implementação (depois dos `fun`). -/
def implHead (env : Environment) (impl : Name) : Option Name := do
  let ci ← env.find? impl
  let v ← ci.value? (allowOpaque := true)
  (stripLams v).getAppFn.constName?

/-- Forma do `ctorIdx` gerado pelo Lean (v4.36.0-rc1, `mkCtorIdx`/`mkCtorIdxImpl`). -/
def ctorIdxShape (env : Environment) (n impl : Name) : Bool := Id.run do
  let .str ind "ctorIdx" := n | return false
  let some (.inductInfo _) := env.find? ind | return false
  unless impl == Name.mkStr n "_impl" do return false
  let some (.defnInfo v) := env.find? impl | return false
  unless v.safety == .unsafe do return false
  match implHead env impl with
  | some h => return h.getString! == "getObjTagNat" && (moduleOf env h).any (·.getRoot == `Init)
  | none => return false

def rangeJ (env : Environment) (n : Name) : Json :=
  match declRangeExt.find? (level := .server) env n with
  | some r => Json.arr #[toJson r.range.pos.line, toJson r.range.endPos.line]
  | none => Json.null

def oleanOf (env : Environment) (n : Name) : IO (Option String) := do
  let some m := moduleOf env n | return none
  try pure (some (← IO.FS.realPath (← findOLean m)).toString) catch _ => pure none

def dump (env : Environment) (root : Name) : IO Json := do
  let mut out := #[]
  let mut total := 0
  for (n, ci) in env.constants.toList do
    total := total + 1
    let impl? := Compiler.implementedByAttr.getParam? env n
    let ext := isExtern env n
    if impl?.isNone && !ext then continue
    let mut fields : List (String × Json) := [
      ("name", toJson n.toString), ("kind", toJson (kindOf ci)),
      ("extern", toJson ext),
      ("module", toJson ((moduleOf env n).map toString)), ("olean", toJson (← oleanOf env n)),
      ("range", rangeJ env n), ("user_facing", toJson (isUserFacing n))]
    if let some impl := impl? then
      fields := fields ++ [("implementation", toJson impl.toString),
        ("implementation_head", toJson ((implHead env impl).map toString)),
        ("ctor_idx_shape", toJson (ctorIdxShape env n impl))]
    out := out.push (Json.mkObj fields)
  let mut reportableCount := 0
  for i in Array.range env.header.moduleNames.size do
    let m := env.header.moduleNames[i]!
    unless inRoot root m do continue
    for n in env.header.moduleData[i]!.constNames do
      if reportable env n then reportableCount := reportableCount + 1
  return Json.mkObj [("root", toJson root.toString), ("lean_version", toJson Lean.versionString),
    ("constants", toJson total), ("reportable_in_root", toJson reportableCount),
    ("attributed", Json.arr out)]

def reach (env : Environment) (root : Name) (seedsJ : Json) : IO Json := do
  let cats ← IO.ofExcept (seedsJ.getObjValAs? (Array String) "categories")
  let seedsObj ← IO.ofExcept (seedsJ.getObjVal? "seeds")
  let seedList ← IO.ofExcept (seedsObj.getObj?)
  -- numeração das constantes
  let mut ids : Std.HashMap Name Nat := {}
  let mut names : Array Name := #[]
  for (n, _) in env.constants.toList do
    ids := ids.insert n names.size
    names := names.push n
  -- grafo reverso
  let mut rev : Array (Array Nat) := Array.replicate names.size #[]
  for i in Array.range names.size do
    let some ci := env.find? names[i]! | continue
    let mut seen : NameSet := {}
    for d in directDeps ci do
      if seen.contains d then continue
      seen := seen.insert d
      if let some j := ids[d]? then
        rev := rev.modify j (·.push i)
  -- sementes pelo TEXTO do nome: nomes higiênicos (`inst._@.M._hyg.8`) não voltam de texto
  -- para `Name` (o componente numérico vira texto)
  let mut seedCat : Std.HashMap String Nat := {}
  for ⟨k, v⟩ in seedList.toArray do
    if let some idx := v.getNat?.toOption then seedCat := seedCat.insert k idx
  let mut seedIds : Array (Nat × Nat) := #[]
  let mut found : Std.HashSet String := {}
  for i in Array.range names.size do
    let s := names[i]!.toString
    if let some c := seedCat[s]? then
      seedIds := seedIds.push (i, c)
      found := found.insert s
  let missingSeeds := seedCat.toArray.filterMap fun (k, _) => if found.contains k then none else some k
  -- busca por categoria
  let mut mask : Array UInt32 := Array.replicate names.size 0
  for c in List.range cats.size do
    let bit : UInt32 := (1 : UInt32) <<< c.toUInt32
    let mut stack : Array Nat := seedIds.filterMap fun (i, c') => if c' == c then some i else none
    while h : stack.size > 0 do
      let i := stack.back
      stack := stack.pop
      if mask[i]! &&& bit != 0 then continue
      mask := mask.set! i (mask[i]! ||| bit)
      for j in rev[i]! do
        if mask[j]! &&& bit == 0 then stack := stack.push j
  -- declarações reportáveis da raiz
  let mut byMask : Std.HashMap UInt32 Nat := {}
  let mut examples : Std.HashMap UInt32 (Array String) := {}
  let mut byArea : Std.HashMap String (Array Nat) := {}
  let mut total := 0
  for i in Array.range env.header.moduleNames.size do
    let m := env.header.moduleNames[i]!
    unless inRoot root m do continue
    let area := match m.components with
      | _ :: a :: _ :: _ => s!"{root}.{a}" | _ => root.toString
    for n in env.header.moduleData[i]!.constNames do
      unless reportable env n do continue
      total := total + 1
      let some id := ids[n]? | continue
      let mk := mask[id]!
      byMask := byMask.insert mk (byMask.getD mk 0 + 1)
      if mk != 0 then
        let ex := examples.getD mk #[]
        if ex.size < 25 then examples := examples.insert mk (ex.push n.toString)
        let row := byArea.getD area (Array.replicate (cats.size + 1) 0)
        let row := row.modify 0 (· + 1)
        let row := (List.range cats.size).foldl (init := row) fun r c =>
          if mk &&& ((1 : UInt32) <<< c.toUInt32) != 0 then r.modify (c + 1) (· + 1) else r
        byArea := byArea.insert area row
  let masksJ := byMask.toArray.qsort (·.1 < ·.1) |>.map fun (mk, cnt) =>
    Json.mkObj [("mask", toJson mk.toNat), ("count", toJson cnt),
      ("categories", toJson ((List.range cats.size).filter (fun c => mk &&& ((1 : UInt32) <<< c.toUInt32) != 0)
        |>.map (cats[·]!))),
      ("examples", toJson (examples.getD mk #[]))]
  let areasJ := byArea.toArray.qsort (·.1 < ·.1) |>.map fun (a, row) =>
    Json.mkObj [("area", toJson a), ("affected", toJson row[0]!),
      ("by_category", Json.mkObj ((List.range cats.size).map fun c => (cats[c]!, toJson row[c + 1]!)))]
  return Json.mkObj [("root", toJson root.toString), ("categories", toJson cats),
    ("constants", toJson names.size), ("reportable_in_root", toJson total),
    ("missing_seeds", toJson missingSeeds), ("masks", Json.arr masksJ), ("areas", Json.arr areasJ)]

def main (args : List String) : IO UInt32 := do
  initSearchPath (← findSysroot)
  match args with
  | ["dump", rootS, outP] =>
    let root := rootS.toName
    let env ← importModules #[{module := root}] {} (loadExts := false)
    IO.FS.writeFile outP ((← dump env root).compress ++ "\n")
    return 0
  | ["reach", rootS, seedsP, outP] =>
    let root := rootS.toName
    let seedsJ ← IO.ofExcept (Json.parse (← IO.FS.readFile seedsP))
    let env ← importModules #[{module := root}] {} (loadExts := false)
    IO.FS.writeFile outP ((← reach env root seedsJ).compress ++ "\n")
    return 0
  | _ =>
    IO.eprintln "uso: implemented_by_scan dump <Raiz> <saída.json> | reach <Raiz> <sementes.json> <saída.json>"
    return 2
