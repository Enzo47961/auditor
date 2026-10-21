# TCB (Trusted Computing Base) — manifesto

Todo selo é emitido **contra uma TCB enumerada**. Um componente da TCB é algo em que o selo confia e que a ferramenta **não audita**. Se qualquer um deles estiver errado, o selo pode estar errado, e a ferramenta não tem como detectar isso.

Cada relatório traz a TCB em `tcb` (no nível do relatório e repetida em cada declaração). Se algum componente obrigatório estiver ausente, nenhuma declaração sai `Validada`: o agregador aplica `tcb_incomplete`, e o JSON Schema v1 rejeita `Validada` com TCB incompleta.

## Componentes

| Campo em `tcb` | Componente | Identificação | Por que é confiado |
|---|---|---|---|
| `kernel` | kernel do Lean | `lean_version`, `githash` (lidos do próprio Lean pelo inspetor) | É a âncora: decide se um termo prova um enunciado. Não é auditado (princípio "kernel é TCB, não oráculo"). |
| `toolchain` | elaborador, compilador, runtime e `lake` do toolchain fixado | `lean_toolchain` exato; `library_roots` declaradas pelo toolchain | Produz os `.olean` que o inspetor lê. Com `native_decide`, a confiança se estende ao compilador e ao runtime (L-1), e às implementações nativas do toolchain (ver "Fronteira de TCB"). |
| `dependencies` | Mathlib e demais pacotes | `lake_manifest_sha256`; `packages` (nome, tipo, rev); `project_commit` e `project_dirty` (quando a raiz do projeto é um repositório git); `mathlib_commit` (rev do pacote `mathlib`, ou o commit do projeto quando o projeto é o próprio Mathlib) | O conteúdo das dependências é elaborado pelo kernel, mas as regras de fronteira e os metadados dependem de quais pacotes estão presentes. |
| `inspector` | metaprograma Lean da Etapa B (`src/auditor/lean/Inspect.lean`) | `version`, `source_sha256`, `binary_sha256` | Lê o ambiente elaborado. Se omitir uma declaração ou um axioma, o agregador não sabe. Mitigações em L-14. O binário é compilado por plataforma, então o hash difere entre sistemas operacionais. |
| `aggregator` | código Python do pacote `auditor` (Etapa A, wrapper da Etapa B, política, agregador, relatório) e suas dependências Python | `version`, `source_sha256` (hash de todos os `.py` do pacote), `python`, `python_dependencies` (fecho transitivo instalado, com versões exatas: `jsonschema`, `referencing`, `rpds-py`, `attrs`, …; D-20) | Aplica a política, valida o relatório contra o schema e emite o selo. Dependência não resolvível → TCB incompleta → nenhuma `Validada`. |
| `stage_a_parser` | varredura léxica e allow-list de comandos | `version`; `allowlist` (tipo, toolchain, `env_pin`, versões do gerador e da classificação) | Captura o que não existe no ambiente elaborado (`set_option`, sintaxe nova, Unicode). |
| `policy` | `policy.toml` | `version`, `sha256` do arquivo | Define o que é admissão, proibido, permitido e desconhecido. |
| `metadata` | atributos importados transitivamente | contagem e SHA-256 da lista ordenada de `@[simp]`, `@[ext]`, `@[reducible]`, `@[implemented_by]` | Mudanças nesses atributos mudam o comportamento das táticas; entram no fingerprint para invalidar selos (princípio 7). |
| `fingerprint` | — | SHA-256 da forma canônica (JSON com chaves ordenadas) de todos os campos acima | Identifica o ambiente contra o qual o selo foi emitido. |

**O fingerprint não contém caminhos absolutos**, porque identifica o ambiente, não a máquina. Ele contém o hash do binário do inspetor, que é específico da plataforma; o mesmo ambiente em sistemas operacionais diferentes produz fingerprints diferentes.

**O que não está na TCB, porque não é confiado nem verificado:** a correspondência entre enunciado formal e informal (sempre `Não auditada`), a semântica das provas e os contextos construtivos. Esses itens estão listados em `not_covered` e na string do selo.

## Fronteira de TCB

A especificação original não tinha esta seção, e duas decisões tropeçaram na falta dela:
- **O-1:** a justificativa de `native_decide` aceita confiar no compilador e no runtime.
- **Q7:** `@[extern]`/`@[implemented_by]` do próprio toolchain estão no caminho de quase toda prova.

Esta seção fecha a lacuna de forma sistemática, não só para a Q7.

**Decisão (Q7, opção a).** A confiança é transitiva a partir do kernel e das dependências que o toolchain declara. As regras de `@[extern]` e `@[implemented_by]` (candidato; padrão combinado com `Lean.ofReduceBool`/`Lean.ofReduceNat` → `Rejeitada`) só se aplicam a declarações **user-level**. Declarações **Lean-level** são TCB e não disparam as regras. `native_decide` de usuário continua exigindo justificativa; desde a v4.36 ele também nunca sai `verified` (Q9-a, L-19). **Medição que confirma a Q9-a** (Mathlib `e1b2403b`, `tools/layer2/native_usage.py`): na biblioteca `Mathlib`, 0 provas usam avaliação nativa (2 de 256 505 declarações são detectadas pela contagem léxica, e as duas são código de metaprogramação: o linter que proíbe a avaliação nativa e um campo de configuração). Em `MathlibTest`, 33 de 7 463 (0,44 %). O caso da tática importada (`inclusion +native`, que chama `nativeEqTrue` direto) gera `…._native.inclusion.ax_…` e é pego pela forma do axioma. O impacto da Q9-a fica confinado a `MathlibTest`, onde `native_decide` aparece legitimamente. `Nat.add` (`@[extern]` do toolchain) não dispara nada (cenário 06).

### (i) A fronteira é declarada, não inferida pelo nome

Duas fontes declaram a fronteira. O nome do módulo nunca decide, porque um pacote do usuário pode ter um módulo chamado `Init.Algo`.

- **O toolchain fixado declara suas raízes de biblioteca:** os `.olean` de primeiro nível em `<sysroot>/lib/lean`. No `leanprover/lean4:v4.36.0-rc1` são `Init`, `Lake`, `LakeMain`, `Lean`, `LeanChecker`, `LeanExport`, `LeanIR`, `Leanc` e `Std` (na v4.22.0 eram seis: sem `LeanChecker`, `LeanExport` e `LeanIR`).
- **Das raízes declaradas, só as `target_trusted_roots` são TCB** (D-42, D-47). O arquivo é `src/auditor/data/target_trusted_roots/<toolchain>.json`. **O que ele significa:** as raízes do toolchain cujos módulos são implicitamente confiáveis no fecho do projeto-alvo, isto é, as que o alvo usa. **O que ele não significa:** "todas as raízes da TCB do Lean". Uma raiz declarada pelo toolchain e fora dessa lista continua sendo código do Lean, mas, para o auditor, os módulos dela são tratados como user-level: as regras de `@[extern]`/`@[implemented_by]` se aplicam (fail-closed).
  - O arquivo é gerado por `tools/gen_tcb_roots.py` a partir do fecho de imports da biblioteca do Mathlib no commit fixado, com as dependências nas revisões exatas do seu `lake-manifest.json`. Ele registra o commit do projeto, o SHA-256 do manifest, a revisão de cada pacote e quantos módulos de cada raiz o fecho usa. O próprio JSON traz o campo `meaning` com a definição acima.
  - Em tempo de execução, o arquivo precisa ser consistente com o toolchain. Se faltar o arquivo para o toolchain do projeto, se ele declarar outro toolchain, se a lista de raízes declaradas gravada nele diferir da do sysroot (drift), ou se uma raiz dele não for declarada pelo toolchain, o resultado é `tcb_boundary_undeclared` (exit 2).
  - **Escopo explícito** (`v4.36.0-rc1`, Mathlib `e1b2403b`):

    | Raiz | Declarada pelo Lean v4.36.0-rc1 | Usada pelo Mathlib `e1b2403b` (módulos no fecho) | Em `target_trusted_roots` do auditor |
    |---|---|---|---|
    | `Init` | sim | sim (668) | sim |
    | `Lean` | sim | sim (741) | sim |
    | `Std` | sim | sim (215) | sim |
    | `Lake` | sim | sim (1: `Lake.Util.Casing`, via `Mathlib.Tactic.Linter.TextBased`) | sim |
    | `LakeMain` | sim | não | não |
    | `Leanc` | sim | não | não |
    | `LeanChecker` | sim | não | não |
    | `LeanExport` | sim | não | não |
    | `LeanIR` | sim | não | não |

    As duas últimas colunas são iguais por construção: o arquivo é o fecho medido. Se uma prova passar a importar, por exemplo, `LakeMain` (a ferramenta de build, não matemática), isso é suspeito, e o auditor trata o módulo como user-level (fail-closed). Projeto-alvo que não é o Mathlib: L-21.
- **O `lake-manifest.json` declara os pacotes do usuário.** Cada pacote (`git`: `<packagesDir>/<nome>`; `path`: `dir`), além do próprio projeto, contribui uma raiz de usuário `<pacote>/.lake/build/lib/lean`.

O `<sysroot>` é obtido de duas formas independentes: pelo inspetor (`findSysroot`, sob `lake env`) e pelo elan (`lean --print-prefix` na raiz do projeto). As duas precisam coincidir; senão, `sysroot_mismatch` (exit 2). O search path efetivo do inspetor também é conferido: toda entrada precisa ser o diretório do toolchain ou uma raiz derivada do manifest; senão, `search_path_unrecognized` (exit 2).

### Algoritmo

Implementado em `src/auditor/tcb_boundary.py`, com testes unitários em `tests/tcb/test_boundary.py`.

**Entrada:**
- o módulo `M` de origem da constante com o atributo;
- o caminho real `P` do seu `.olean`, resolvido pelo search path efetivo do inspetor;
- o manifest;
- o sysroot.

**Passos:**
1. Se `P` está sob uma raiz de usuário e não sob `<sysroot>/lib/lean`, o resultado é **user**.
2. Se `P` está sob `<sysroot>/lib/lean` e não sob raiz de usuário, o resultado é **tcb** somente se as três condições abaixo valem:
   - (a) a raiz do nome de `M` é declarada pelo toolchain **e** está em `target_trusted_roots` (senão, razão `module_root_not_declared_by_toolchain` ou `module_root_not_used_by_target_project`);
   - (b) `P` é exatamente `<sysroot>/lib/lean/<M como caminho>.olean`;
   - (c) nenhuma raiz de usuário fornece um `.olean` para `M` (sombreamento).
3. Em qualquer outro caso, o resultado é **unresolved**: a declaração fica `Não resolvida`, razão `tcb_boundary_unresolved` (fail-closed).

Manifest com versão fora de `1.x`, pacote sem nome, tipo de pacote desconhecido, pacote `path` sem `dir`, ou toolchain sem raízes declaradas → `tcb_boundary_undeclared` (exit 2).

### (ii) Mudança de fronteira exige revisão da política

A fronteira depende do toolchain fixado. Ao subir o `lean-toolchain`:
1. regenerar `target_trusted_roots` (`docs/maintenance.md`, passo 8) e rodar `tests/tcb`, `tests/stage_b` e `tests/conformance/test_06_tcb_boundary.py`. O canário confere a lista exata de raízes declaradas, e o cenário 06 tem uma declaração por raiz da allow-list, que precisa sair TCB;
2. se as raízes mudaram, ou se uma implementação nativa mudou de módulo, a política precisa ser revista por alguém que não é o autor da mudança, como qualquer mudança de regra;
3. registrar a mudança no histórico de `policy.toml` (`policy_version`).

### (iii) O canário: `06-tcb-boundary`

O cenário `tests/conformance/06-tcb-boundary` usa `Nat.add` (`@[extern]` de `Init.Prelude`) com e sem `native_decide` e exige que nenhuma regra de `@[extern]`/`@[implemented_by]` dispare nos dois casos (sem `native_decide`: `verified`; com: `unresolved` só pelo axioma auxiliar nativo, Q9-a). Sem esse teste, a opção (a) seria afirmação não testada. Ele falha se:
- o Lean mudar onde `Nat.add` vive;
- o Lean deixar de declarar `Init` como raiz;
- a classificação passar a marcar implementações do toolchain como user-level ou indecidíveis;
- `target_trusted_roots` deixar de reconhecer uma raiz que o Mathlib usa. Há uma sonda por raiz:
  `uses_init` (`Nat.add`), `uses_lean` (`Lean.Expr.quickLt`), `uses_std` (`ByteSlice.beq`) e
  `uses_lake` (`Lake.JobTask.toOpaque`, `@[implemented_by]`). O teste confere que as raízes da
  lista são exatamente as sondadas, então raiz nova sem sonda também falha (D-49). A
  mutação "remover a raiz X de `target_trusted_roots`" é detectada para cada uma das quatro raízes.

O caso (c) do `04b-extern` testa o lado oposto: `@[extern]` de usuário que mente, junto com `Nat.add` no mesmo enunciado, sai `Rejeitada`, e só `myF` é apontado.

### Limites desta fronteira

- Um bug no runtime ou no compilador do Lean fica fora do alcance. Isso já valia antes da Q7 (L-1).
- `@[implemented_by]` em pacotes do usuário, inclusive o Mathlib, continua disparando as regras. A magnitude no Mathlib só aparece nas medições da camada 2.

## O inspetor não executa código do ambiente importado (D-39)

Desde a v4.36, carregar as extensões do ambiente (`importModules (loadExts := true)`) exige `enableInitializersExecution`, que executa os `initialize` dos módulos importados — inclusive os do PR auditado — dentro do processo do inspetor. Código do PR rodando no inspetor poderia reescrever os fatos que ele emite. Por isso o inspetor importa com `loadExts := false` e lê cada extensão pelas entradas gravadas em cada módulo (`getModuleEntries`), que a importação disponibiliza sem executar nada.

Consequência para `#print axioms`: na v4.36, `Lean.collectAxioms` usa, para declarações importadas, axiomas pré-calculados gravados em cada `.olean` (`exportedAxiomsExt`). Sem as extensões carregadas, essa tabela está vazia e o algoritmo percorre os corpos de todas as constantes. O resultado do auditor, portanto, não depende de um resumo gravado no `.olean` pelo build do PR. A comparação entre o resumo gravado e o percurso dos corpos não é feita (o estado e a extensão são privados ao módulo `Lean.Util.CollectAxioms`); ver L-20.

O gerador da allow-list (`Dump.lean`) é a única peça que executa initializers: o parser de comandos dos módulos só existe com as extensões carregadas. Ele roda em manutenção, sobre código revisado (o core do toolchain, ou o projeto num commit aceito), nunca sobre código de PR.
