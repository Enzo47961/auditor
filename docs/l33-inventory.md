# L-33 — inventário do código do usuário executado na elaboração (Fase 1)

```
fonte: leanprover/lean4 v4.36.0-rc1 (commit c9afcddf), Mathlib e1b2403b; citações geradas do fonte fixado
classificação: author-self-review (L-26)
```

**Pergunta.** Que táticas, termos, comandos e atributos executam código **do usuário** durante a elaboração do arquivo, antes que a Etapa B veja o ambiente? O critério é o da L-17, emendado pela L-33a: vale para comando, tática, termo ou atributo.

**Varredura.**
- Expressões procuradas no fonte do Lean (`Lean/`, `Std/`, `lake/`): `evalExpr`, `evalExpr'`, `evalTerm`, `evalConst`, `evalConstCheck`, `runTermElab`, `runCommandElabM`, `addAndCompile`.
- As mesmas expressões no Mathlib.
- Também os registros de atributo (`registerBuiltinAttribute`, `KeyedDeclsAttribute.init`, `mkElabAttribute`, `registerInitAttr`).
- Para cada ponto de avaliação, identifiquei a sintaxe do usuário que o aciona.
- Lista bruta: `trabalho/l33/grep_eval.txt`, com 232 linhas.
- As citações abaixo foram geradas por script a partir do fonte fixado, não copiadas à mão (regra da revisão independente, `roadmap.md`).

**Três maneiras de o código do usuário chegar a ser executado:**
1. **No ponto em que aparece.** O código é avaliado e descartado (`withoutModifyingEnv`), então só o texto o revela. Defesa: **léxica**.
2. **Registrado no ambiente e executado depois.** Um atributo registra a declaração do usuário como elaborador, tática, simproc, linter, `init` etc., e o elaborador a executa quando a situação aparece. A declaração fica no ambiente com um tipo que alcança `IO.RealWorld`, pois toda mônada de meta-programação é construída sobre `EIO`. Defesa: **por ambiente**, na Etapa B.
3. **Termo do usuário avaliado como dado.** É o caso de configuração de tática, `include_str`, `autoParam`, `eval%` e widgets. Um termo puro não faz IO. Para fazer, precisa de uma saída de escape:
   - `unsafe` (léxico);
   - `@[extern]` (por ambiente);
   - `implemented_by` para uma implementação `unsafe` (léxico, pelo `unsafe`);
   - código de outro arquivo do PR (dependência, abaixo).

## Decisões implementadas (Etapa A v4, inspetor v5)

| Mecanismo | Defesa | Resultado |
|---|---|---|
| `run_tac`, `by_elab` no arquivo | léxica, em qualquer posição (`elaboration_code_execution`) | **Rejeitada**: a execução é violação concreta (`elaboration_executes_code`, em `policy_violations`) |
| `unsafe` no arquivo (modificador ou termo) | léxica, em qualquer posição (`unsafe_code`) | Não resolvida (`stage_a_unrecognized`) |
| Constante do módulo-alvo cujo **tipo** alcança `IO.RealWorld`, ou com `@[extern]` | **por ambiente** (inspetor v5, `execution_capable`) | Não resolvida (`target_defines_executable_code`). Registrar não prova que executou |
| Arquivo alterado no PR, importado pelo alvo, com `run_tac`/`by_elab` (ou ilegível) | léxica no arquivo alterado + `imports` do inspetor; o `auditor-ci` passa os alterados (`--changed`) | Não resolvida (`dependency_executes_code`) |
| `show_panel_widgets` | classificação do core: era `allowed`, passou a `metaprogramming` (classificação v5) | Não resolvida, como `#widget` |
| Comandos que avaliam código (`#eval`, `#guard`, `#widget`, `run_cmd`…) | classificação (L-17), já fail-closed | Não resolvida |
| Avaliação nativa (`native_decide`, `decide +native`) | Etapa B (Q9) | Rejeitada / Não resolvida, como antes |

**O que fica fora da defesa léxica e por ambiente, e por quê:**
- **Código de uma dependência não alterada no PR.** É o Mathlib ou outra biblioteca no commit fixado, já revisado no branch base. Mesma premissa da TCB de bibliotecas.
- **Código de dependências externas do Mathlib.** Batteries, Aesop, Qq, ProofWidgets, Plausible, LeanSearchClient e importGraph **não foram inventariados**: só o core e o Mathlib foram. Fica declarado na L-33a.
- **Uma dependência alterada que registra código (via 2 ou 3) sem `run_tac`/`by_elab`.** Ela é auditada como alvo, e sai Não resolvida (`target_defines_executable_code` ou `unsafe_code`). O alvo que a importa **não** herda a sinalização: o cruzamento por dependência só usa o achado léxico. Declarado na L-33a.
- **`lakefile.lean` alterado no PR.** O Lake executa código da configuração (``lake/Lake/Load/Lean/Eval.lean:130``). Está fora do alcance da Etapa A, que audita os módulos do projeto.
- Contra **qualquer** mecanismo não inventariado, a defesa é a mitigação estrutural (b) da instrução 24: hash do inspetor e do auditor antes e depois do `lake build` (`roadmap.md`).

## 1. Execução no ponto (léxico)

**`run_tac`** (tática): avalia o bloco `do` como `TacticM Unit`. `Lean/Elab/Tactic/BuiltinTactic.lean:683–685`

```lean
  match stx with
  | `(tactic| run_tac $e:doSeq) =>
    ← unsafe Term.evalTerm (TacticM Unit) (mkApp (Lean.mkConst ``TacticM) (Lean.mkConst ``Unit))
```

**`by_elab`** (termo): avalia o bloco como `TermElabM Expr`. `Lean/Elab/BuiltinNotation.lean:585–588`

```lean
  | `(by_elab $cmds:doSeq) => do
    if let `(Lean.Parser.Term.doSeq| $e:term) := cmds then
      if e matches `(Lean.Parser.Term.doSeq| fun $[$_args]* => $_) then
        let tac ← unsafe evalTerm
```

Demonstrado na Fase 1: os dois gravaram um arquivo durante o `lake build`, e o auditor dava `verified`, exit 0 (L-33). Cenário de conformidade 09.

## 2. Comandos que avaliam código (classificação, L-17)

Já fail-closed antes da Fase 1: `#eval` `Lean/Elab/BuiltinEvalCommand.lean:193–194`

```lean
        let declName ← addAndCompileExprForEval declName e (allowSorry := bang)
        let mf : m Unit ← evalConst (m Unit) declName (checkMeta := !Elab.inServer.get (← getOptions))
```
`#guard` `Lean/Elab/Tactic/Guard.lean:160–163`

```lean
    let e ← instantiateMVars e
    let mvars ← getMVars e
    if mvars.isEmpty then
      let v ← unsafe evalExpr (checkMeta := false) Bool (mkConst ``Bool) e
```
`#widget` `Lean/Widget/Commands.lean:110–113`

```lean
@[command_elab widgetCmd] meta def elabWidgetCmd : CommandElab
  | stx@`(#widget $s) => liftTermElabM do
    let wi : Expr ← elabWidgetInstanceSpec s
    let wi : WidgetInstance ← evalWidgetInstance wi
```
`register_error_explanation` `Lean/Elab/ErrorExplanation.lean:105–107`

```lean
    let e ← elabTermEnsuringType t tp
    if e.hasSyntheticSorry then throwAbortTerm
    evalExpr ErrorExplanation.Metadata tp e
```
`test_extern` `Lean/Util/TestExtern.lean:32–34`

```lean
        let t' := (← unfold t f).expr
        let r ← mkDecide (← mkEq t t')
        if ! (← evalExpr Bool (.const ``Bool []) r) then
```

**`show_panel_widgets`, reclassificado** (era `allowed`; avalia o termo da instância de widget, como `#widget`): `Lean/Widget/Commands.lean:72–75`

```lean
      | `(showWidgetSpec| $attr:attrKind $spec:widgetInstanceSpec) =>
        let attr ← liftMacroM <| toAttributeKind attr
        let wiExpr ← elabWidgetInstanceSpec spec
        let wi ← evalWidgetInstance wiExpr
```

**`postprocess_traces`**: avalia o pós-processador. `Lean/PostprocessTraces/Basic.lean:244–245`

```lean
    -- argument `TracePostprocessor`
    unsafe Meta.evalExpr TracePostprocessor type e
```
É sintaxe `scoped`:
`Lean/PostprocessTraces/PostprocessTracesCommand.lean:45–46`

```lean
scoped syntax (name := postprocessTracesCmd)
  "postprocess_traces " term " in" ppLine command : command
```

Não está na tabela de comandos de nenhuma allow-list; usada na coluna 0 depois de `open`, sai `unknown_command` (fail-closed). Do Mathlib, `lrat_proof` (já `metaprogramming`): `Mathlib/Tactic/Sat/FromLRAT.lean:624–625`

```lean
  Command.liftTermElabM do
    let cnf ← unsafe evalTerm String (mkConst ``String) cnf
```

`#find_syntax` (Mathlib, `allowed`) avalia os `ParserDescr` do ambiente: `Mathlib/Tactic/FindSyntax.lean:67–68`

```lean
    if prsr.contains cinfo.type && !declName.isInternal then
      let descr ← unsafe evalConst ParserDescr declName
```
Um parser do usuário exige `syntax`/`elab` (fail-closed) ou `unsafe` (léxico). Mantido `allowed`.

## 3. Atributos que registram a declaração do usuário (por ambiente)

Em todos os casos, o elaborador avalia a declaração decorada com `evalConst`/`evalConstCheck` e a executa quando a situação aparece, inclusive mais adiante no mesmo arquivo.
- O tipo dessas declarações (`Tactic`, `TermElab`, `CommandElab`, `Macro`, `Simproc`, `Parser`, `IO Unit`, `NormNumExt`…) alcança `IO.RealWorld`.
- Isso é detectado pelo inspetor v5 (`execution_capable`), sem lista de nomes de atributo. Os nomes de sintaxe diferem dos registrados (por exemplo, o atributo registrado como `PolyInferBaseAttr` se escreve `polynomial_infer_base`), e uma lista léxica seria frágil.

| Atributo (família) | Avaliação |
|---|---|
| `term_elab`, `command_elab`, `tactic`, `macro`, `doElem_elab`, `grind_tactic`, `sym_simproc`, `try_tactic`, `quot_precheck`, `inductive_elab`, `delab`… (`KeyedDeclsAttribute`) | `Lean/KeyedDeclsAttribute.lean:166` |
| atributos de parser (`term_parser`, `command_parser`, `<categoria>_parser`) | `Lean/Parser/Extension.lean:269` |
| `simproc`, `dsimproc` | `Lean/Meta/Tactic/Simp/Simproc.lean:130` |
| `cbv_simproc` | `Lean/Meta/Tactic/Cbv/CbvSimproc.lean:162` |
| `init` (`initialize`) | `Lean/Compiler/InitAttr.lean:193` — roda nos arquivos que **importam** (cenário 10) |
| `env_linter` | `Lean/Linter/EnvLinter/Basic.lean:59` |
| `missing_docs_handler` | `Lean/Linter/MissingDocs.lean:43` |
| `unused_variables_ignore_fn` | `Lean/Linter/UnusedVariables.lean:143` |
| `cpass` (passes do compilador) | `Lean/Compiler/LCNF/PassManager.lean:217` |
| `try_suggestion` | `Lean/Elab/Tactic/Try.lean:1033` |
| `library_suggestions` | `Lean/LibrarySuggestions/Basic.lean:508` |
| `frameproc` | `Lean/Elab/Tactic/VCGen/FrameProcAttr.lean:29` |
| `formatter`, `parenthesizer` (combinadores) | `Lean/ParserCompiler/Attribute.lean:53` |
| implementação de atributo (`AttributeImpl`) | `Lean/Attributes.lean:454` |
| papéis de docstring Verso | `Lean/Elab/DocString/Builtin/Keywords.lean:203` |
| Mathlib: `norm_num` | `Mathlib/Tactic/NormNum/Core.lean:69` |
| Mathlib: `positivity` | `Mathlib/Tactic/Positivity/Core.lean:100` |
| Mathlib: `polynomial_infer_base` | `Mathlib/Tactic/Polynomial/Core.lean:57` |
| Mathlib: `gcongr_forward` | `Mathlib/Tactic/GCongr/ForwardAttr.lean:27` |
| Mathlib: `bareiss_ext` | `Mathlib/Tactic/Echelon/Core.lean:253` |
| Mathlib: extensões de `inclusion` | `Mathlib/Tactic/Inclusion/Core/DiscrTreeExt.lean:43`; `Mathlib/Tactic/Inclusion/Core/Extensions.lean:139` |
| só no servidor (não roda no `lake build` do CI): `code_action_provider`, `hole_code_action`, `command_code_action`, `server_rpc_method` | `Lean/Server/CodeActions/Attr.lean:35`; `Lean/Server/Rpc/RequestHandling.lean:31` |

Citações representativas: `Lean/KeyedDeclsAttribute.lean:164–166`

```lean
      match IR.getSorryDep (← getEnv) declName with
      | none =>
        let val ← evalConstCheck γ df.valueTypeName declName
```
`Lean/Meta/Tactic/Simp/Simproc.lean:128–130`

```lean
    match info.type with
    | .const ``Simproc _ =>
      return .inl (← IO.ofExcept <| ctx.env.evalConst Simproc ctx.opts declName)
```
`Lean/Compiler/InitAttr.lean:190–193`

```lean
      continue
    if initDecl.isAnonymous then
        -- Don't check `meta` again as it would not respect `Elab.inServer`
      let initFn ← IO.ofExcept <| env.evalConst (checkMeta := false) (IO Unit) opts decl
```
`Lean/Compiler/InitAttr.lean:88–89`

```lean
/--
Registers an initialization procedure. Initialization procedures are run in files that import the
```
`Mathlib/Tactic/NormNum/Core.lean:68–69`

```lean
  let { env, opts, .. } ← read
  IO.ofExcept <| unsafe env.evalConstCheck NormNumExt opts ``NormNumExt n
```

**`initialize`, a pergunta 2 do revisor.** A documentação do atributo diz que "Initialization procedures are run in files that import the file they are defined in". `runInitAttrForMod` percorre os módulos **importados**. O cenário 10 (ground truth) confere as duas metades por execução no toolchain fixado:
- compilar o arquivo que declara `initialize` não o executa;
- compilar um arquivo que o importa, executa.

Consequências:
- No **alvo**, o procedimento de `initialize` é uma constante `IO …` do módulo, então o inspetor v5 o marca (`target_defines_executable_code`). Além disso, o comando segue `metaprogramming`.
- Numa **dependência alterada no PR**, o `initialize` executa durante o build do alvo, e a defesa léxica do cruzamento de dependências **não** o pega (só `run_tac`/`by_elab`). Declarado na L-33a; coberto apenas pela mitigação (b).
- Por isso, nenhuma reclassificação de `initialize` para `allowed` é aplicada.

## 4. Termos do usuário avaliados como dado

Executam código do usuário só pela saída de escape (`unsafe` léxico, `@[extern]` por ambiente) ou por código de dependência.

- **Configuração de tática** (`simp (config := e)`, `+opção`): os elaboradores gerados por `declare_config_elab` avaliam a configuração elaborada com `evalExpr'` em modo `unsafe`. `Lean/Elab/Tactic/Config.lean:150–151`

```lean
  `(unsafe def evalUnsafe (e : Expr) : TermElabM $type :=
      Meta.evalExpr' (safety := .unsafe) $type ``$type e
```
`Lean/Elab/Tactic/Config.lean:169–170`

```lean
        try
          let res ← eval c
```

- **`include_str`** avalia o termo do caminho: `Lean/Elab/BuiltinTerm.lean:437–439`

```lean
@[builtin_term_elab includeStr] def elabIncludeStr : TermElab
  | `(include_str $path:term), _ => do
    let path ← evalFilePath path
```

- **`autoParam`** avalia a constante de sintaxe da tática padrão: `Lean/Elab/App.lean:829–832`

```lean
      | false, _, some (.const tacticDecl _) =>
        let env ← getEnv
        let opts ← getOptions
        match evalSyntaxConstant env opts tacticDecl with
```

- **Mathlib, `eval%`** (termo) avalia o argumento: `Mathlib/Tactic/Eval.lean:43–46`

```lean
  let e ← Lean.Elab.Term.elabTermAndSynthesize stx exp
  let e ← instantiateMVars e
  let ee ← Meta.mkAppM ``Lean.toExpr #[e]
  Lean.Meta.evalExpr Expr q(Expr) ee (safety := .unsafe)
```

- **Mathlib, cotas de π** avaliam os racionais escritos na prova: `Mathlib/Analysis/Real/Pi/Bounds.lean:108–109`

```lean
  for l in els do
    let {num, den, ..} ← unsafe Meta.evalExpr ℚ q(ℚ) (← Term.elabTermAndSynthesize l (some q(ℚ)))
```

- **Mathlib, `inclusion`** avalia a verificação compilada: `Mathlib/Tactic/Inclusion/Core/Core.lean:42–43`

```lean
def compileInclusionCheck (inclusionExpr : Expr) : MetaM IntervalBool :=
  unsafe evalExpr IntervalBool (mkConst ``IntervalBool) inclusionExpr
```


## 5. Já cobertos por outras regras

- **Avaliação nativa** (Q9): `Lean/Meta/Native.lean:61–67`

```lean
        addAndCompile decl
    catch ex =>
      throwError m!"Tactic `{tacticName}` failed. Error: {ex.toMessageData}"

    -- Now evaluate the constant, and check that it is true.
    try
      unsafe evalConst Bool auxDeclName
```

- **`ctorIdx` gerado (P0-1).** A implementação é `getObjTagNat`; ela não executa código do usuário. `Lean/Meta/Constructions/CtorIdx.lean:137–139`

```lean
        -/
        let implName ← mkCtorIdxImpl indName info.levelParams declType
        setImplementedBy declName implName
```

