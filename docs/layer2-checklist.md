# Camada 2 — checklist de execução

**Quem executa:** o mantenedor, sob a própria conta. Nada aqui é executado pelo Claude: são ações
públicas (repositório, fork, PRs, comentários) e decisões no meio do caminho (abortar, ajustar,
continuar) são humanas. O Claude analisa o que for trazido.

**Para que serve:** produzir a evidência da camada 2 da Fase 0 (`README.md`, "Status"; roteiro em
`docs/ci.md`). A Fase 0 só fecha com ela; a Fase 1 não começa antes.

Convenções: `$ME` = sua conta GitHub; `$AUD` = commit do auditor fixado no passo 1; comandos em
bash (Git Bash serve). Cada passo tem **Verificar** (o que precisa ser verdade antes de seguir) e,
quando cabe, **Abortar se**. Ao abortar: não tente consertar no meio; traga o que tiver (logs,
`outcome.json`, captura da tela do job) e o número do passo.

---

## 0. Pré-condições (antes de qualquer ação pública)

- [ ] Leu as decisões pendentes da instrução 12 (`docs/proposed-improvements.md`, "Rodada da
      instrução 12"): Q9, D-39 a D-43. A camada 2 **pode** rodar com a Q9 pendente: o comportamento
      atual é fail-closed (nenhum `native_decide` sai `verified`). Se a Q9 for decidida antes,
      melhor: a medição já usa a política final.
- [ ] Decidiu a visibilidade do repositório do auditor. **Restrição técnica:** o workflow do fork
      chama o workflow reutilizável do auditor (`uses: $ME/auditor/...@$AUD`). Um fork público do
      Mathlib só consegue chamar um workflow reutilizável de repositório **público** (ou do mesmo
      dono com acesso configurado para repositórios privados, o que exige que o fork também seja
      privado — e fork de repositório público não pode ser privado). Na prática: auditor público,
      ou copiar o workflow reutilizável para dentro do fork (ver 3b).
- [ ] O Mathlib `master` ainda está no `leanprover/lean4:v4.36.0-rc1`? Conferir:
      `curl -sSfL https://raw.githubusercontent.com/leanprover-community/mathlib4/master/lean-toolchain`.
      Não importa se mudou: a base fica fixada no commit `e1b2403bdd31a2756e30282d62b3fa54cc95c869`
      (o mesmo toolchain do auditor). Anote a data e o commit do `master` no dia, para o relatório.

## 1. Fixar o auditor

```bash
cd <repositório do auditor>
git status                      # Verificar: limpo
git log -1 --format=%H          # este é o $AUD
```

Se for publicar no GitHub (decisão do passo 0):

```bash
gh repo create $ME/auditor --public --source . --remote origin --push   # ou --private (ver 0)
```

**Verificar:** `gh api repos/$ME/auditor/commits/$AUD --jq .sha` imprime `$AUD`.

## 2. Fork do Mathlib com base fixada

```bash
gh repo fork leanprover-community/mathlib4 --clone=false        # cria $ME/mathlib4
git clone --filter=blob:none https://github.com/$ME/mathlib4 && cd mathlib4
git fetch https://github.com/leanprover-community/mathlib4 e1b2403bdd31a2756e30282d62b3fa54cc95c869
git switch -c auditor-base FETCH_HEAD
cat lean-toolchain              # Verificar: leanprover/lean4:v4.36.0-rc1
```

**Desligar os workflows do próprio Mathlib no fork** (eles rodariam em todo PR, em runners do
GitHub, e poluiriam a medição): no branch `auditor-base`, remover `.github/workflows/*` do Mathlib
antes do passo 4 (`git rm -r .github/workflows`), ou desabilitá-los em Settings → Actions.

**Habilitar Actions no fork:** Settings → Actions → General → "Allow all actions" (forks vêm com
Actions desligado). Workflow permissions: "Read repository contents".

## 3. Allow-list do Mathlib (classificação humana)

```bash
# no clone do fork, branch auditor-base
lake exe cache get                                  # Verificar: termina sem erro
pip install <caminho ou URL do auditor>@$AUD
auditor-gen-allowlist --project .                   # grava .auditor/allowlist.json
python -c "import json;print(json.load(open('.auditor/allowlist.json'))['unclassified'])"
```

- [ ] Para cada comando em `unclassified`, classificar em `.auditor/classification.toml` com o
      critério de `tools/gen_allowlist/classification.toml` (L-17): `metaprogramming` se pode
      executar código compilado na elaboração antes da Etapa B, ou se esconde outro comando da
      checagem de coluna 0; `syntax_extension` se introduz sintaxe; senão, `allowed`. Na dúvida,
      fail-closed. Exemplo de formato em `docs/maintenance.md`, "Allow-list de projeto".
- [ ] Regenerar e conferir: `auditor-gen-allowlist --project . --check` sai com 0 e `unclassified`
      ficou vazio.
- [ ] A classificação é política: outra pessoa revisa antes do commit.

```bash
git add .auditor && git commit -m "auditor: allow-list do Mathlib (e1b2403b, v4.36.0-rc1)"
```

**Abortar se:** `lake exe cache get` falhar; o gerador falhar ao importar o Mathlib (traga a
saída); a lista `unclassified` tiver comandos cujo efeito não dá para determinar lendo a definição.

**Nota de segurança:** o gerador executa os initializers do Mathlib (D-39). Rode-o só sobre o
commit fixado acima, nunca sobre um branch de PR.

## 4. Workflows no fork

```bash
mkdir -p .github/workflows
cp <auditor>/ci/templates/auditor-{tier1,label,report}.yml .github/workflows/
sed -i "s#OWNER/auditor#$ME/auditor#g; s#AUDITOR_SHA#$AUD#g" .github/workflows/auditor-*.yml
grep -n "OWNER\|AUDITOR_SHA" .github/workflows/auditor-*.yml     # Verificar: nada
git add .github/workflows && git commit -m "auditor: workflows (camada 2)"
git push -u origin auditor-base
gh repo edit $ME/mathlib4 --default-branch auditor-base
```

**Por que mudar o branch default:** `workflow_run` (label) e `issue_comment` (`@auditor report`)
só rodam a partir dos workflows do branch default.

**3b (se o auditor não for público):** copiar também `.github/workflows/auditor-tier1.yml` do
auditor para o fork com outro nome (ex.: `auditor-tier1-impl.yml`) e trocar o `uses:` do modelo
para `./.github/workflows/auditor-tier1-impl.yml`. O checkout do auditor dentro do job ainda
precisa de acesso de leitura ao repositório privado (token): nesse caso, pare e me traga a
situação, porque isso muda o modelo de segurança (D-24).

**Verificar:** `gh workflow list -R $ME/mathlib4` mostra `auditor-tier1`, `auditor-label`,
`auditor-report` (e nenhum workflow do Mathlib ativo).

## 5. Primeiro run (cache cold) — não é medição de steady-state

```bash
git switch -c l2-first-run auditor-base
# mudança mínima num arquivo folha: uma linha de comentário
printf '\n-- auditor: primeiro run\n' >> Mathlib/Logic/Hydra.lean
git commit -am "l2: primeiro run" && git push -u origin l2-first-run
gh pr create -R $ME/mathlib4 --base auditor-base --head l2-first-run --title "l2: primeiro run" --body "medição camada 2"
```

**Verificar** (no Job Summary e no `outcome.json` do artefato `auditor-report`):
- `cache_state: cold`, `first_run: true`;
- o job terminou (verde se nada foi rejeitado; vermelho só por rejeição real);
- se passou de 300 s: `cache_cold_extension: true` e label `auditor-first-run` no PR;
- passo "cache do Mathlib (salvar)" rodou sem erro.

**Abortar se:** algum arquivo sair com `allowlist_unavailable`, `toolchain_mismatch`,
`inspector_build_failed`, `sysroot_mismatch` ou `search_path_unrecognized` (falha de ambiente,
não de medição); o job estourar o `timeout-minutes` de 45; o label aplicado for
`auditor-failed-infra` sem explicação no sumário.

## 6. Escolha mecânica dos arquivos

```bash
python <auditor>/tools/layer2/fanout.py . --root Mathlib --top 40 --json fanout.json > fanout.md
```

Resultado observado no commit `e1b2403b` (8651 módulos): as 19 primeiras posições são
infraestrutura (`Mathlib.Init`, `Mathlib.Tactic.*`, `Mathlib.Lean.*`, `Mathlib.Util.*`), que a
Etapa A em geral classifica como metaprogramação (fail-closed) ou que não têm declarações. O
antigo "núcleo" `Mathlib/Logic/Basic.lean` **não existe mais** nesse commit; o equivalente é
`Mathlib/Basic/Logic/Basic.lean` (posição 24, 8072 dependentes). O primeiro módulo matemático do
ranking é `Mathlib/Data/Set/Defs.lean` (posição 20, 8092 dependentes).

Escolha sugerida (o revisor decide e registra):

| PR | Arquivo | Critério |
|---|---|---|
| trivial | `Mathlib/Logic/Hydra.lean` (0 dependentes) ou outro módulo com `transitive = 0` | folha; mudança só de comentário/docstring |
| médio | um arquivo com `imports_transitive` perto da mediana do `fanout.json` (783 no commit `e1b2403b`) | um lema novo, de prova curta |
| maior fanout | `Mathlib/Data/Set/Defs.lean` (primeiro módulo matemático do ranking) **ou** a posição 1 literal, `Mathlib/Init.lean` (8438 dependentes; hoje sem nenhum teorema: só o lema de sonda será auditado), se o revisor quiser o extremo mesmo sendo infraestrutura | um lema novo trivial no fim do arquivo |
| (opcional) pior custo de auditoria | `Mathlib/NumberTheory/LSeries/PrimesInAP.lean` (maior fecho direto: 3403 módulos) | mede o custo do `lake build` + inspetor, que cresce com o fecho direto (D-38) |

## 7. Os 3 PRs de medição (steady-state, depois do passo 5)

Para cada PR (`trivial`, `medio`, `fanout`):

```bash
git switch -c l2-<nome> auditor-base
# editar o arquivo escolhido; para "medio"/"fanout", no fim do arquivo:
#   theorem auditor_probe_<nome> : (2 : Nat) + 2 = 4 := rfl   (Nat, não ℕ: arquivos de base não têm a notação)
git commit -am "l2: <nome>" && git push -u origin l2-<nome>
gh pr create -R $ME/mathlib4 --base auditor-base --head l2-<nome> --title "l2: <nome>" --body "medição camada 2"
```

**Verificar** em cada um:
- `cache_state` é `warm` ou `delta` (nunca `cold` — se for, o cache foi despejado ou a chave mudou:
  abortar esse PR, anotar, rodar de novo);
- `clock_origin: trigger`;
- `auditor_probe_<nome>` aparece no relatório como `verified`;
- tempos: `setup_elapsed_s`, `audit_elapsed_s`, `elapsed_s`, duração do arquivo.

**Abortar se:** o arquivo editado sair `unknown_command` (allow-list incompleta: voltar ao passo 3);
`inspector_disagreement` ou `missing_constants` aparecer (traga o relatório: é achado, não ruído).

## 8. Caminho de timeout (`auditor-failed-infra`)

No branch de um PR novo, editar `.github/workflows/auditor-tier1.yml` do fork e acrescentar em
`with:` a linha `timeout-file-seconds: 5`. Abrir o PR tocando um `.lean`.

**Verificar:** o arquivo sai `timeout` (`timeout_kind: file`), `exit_code: 2`, o job fica **verde**,
e o PR recebe `auditor-failed-infra`. Depois, fechar o PR sem merge.

## 9. Comentário a pedido humano

Num dos PRs do passo 7, um colaborador comenta `@auditor report`.
**Verificar:** aparece um comentário com o sumário, começando por "Pedido por um humano". Um
comentário de alguém sem acesso ao repositório **não** dispara nada.

## 10. Coletar e entregar

```bash
mkdir -p l2 && for pr in <números>; do
  run=$(gh run list -R $ME/mathlib4 --workflow auditor-tier1.yml --branch l2-<nome> --limit 1 --json databaseId --jq '.[0].databaseId')
  gh run download $run -R $ME/mathlib4 -n auditor-report -D l2/pr-$pr
done
python <auditor>/tools/layer2/timings.py l2 > l2/timings.md
```

**Formato esperado do relatório de medição** (um arquivo, ex.: `l2/RELATORIO.md`):

1. Contexto: commit do auditor (`$AUD`), commit base do fork (`e1b2403b`), data, commit do `master`
   do Mathlib no dia, runner (`ubuntu-latest`, versão da imagem no log do job).
2. Tabela, uma linha por PR (primeiro run, trivial, médio, fanout, timeout):

   | PR | arquivo | mudança | `cache_state` | `first_run` | preparação (s) | auditoria (s) | total (s) | duração do arquivo (s) | `exit_code` | contagem verified/rejected/unresolved | labels | conclusão do job |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|

3. `l2/timings.md` (saída do `timings.py`) e `fanout.md` (top 40), com a escolha dos arquivos.
4. Os artefatos completos: `l2/pr-*/outcome.json`, `summary.md`, `report-*.json`.
5. Observações: qualquer abortar/repetir, com o motivo; tamanho de `~/.cache/mathlib` (log do
   passo "cache do Mathlib (salvar)"); se `updated_at` do evento coincidiu com o push (D-30).
