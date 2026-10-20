# Manutenção da allow-list da Etapa A

## O que é mantido e por quem

A allow-list tem duas partes de origem diferente:

| Parte | Origem | Arquivo |
|---|---|---|
| Lista de comandos | **extraída mecanicamente** do toolchain (categoria `command` do parser, via `src/auditor/lean/Dump.lean`) | gerada em `src/auditor/data/allowlist/<toolchain>.json` |
| Classificação de risco (`syntax_extension`, `metaprogramming`) e tokens de continuação | **mantida à mão**, com critério escrito | `tools/gen_allowlist/classification.toml` |

Comando extraído que não está classificado cai em `allowed`. Por isso, **ao subir o toolchain, todo comando novo precisa de revisão humana**: o gerador lista o que mudou, mas não julga o risco.

## Teste de defasagem

`tests/maintenance/test_allowlist_fresh.py` roda `gen.py --check`: roda o extrator com o `lean-toolchain` fixado e falha se o arquivo versionado não corresponder exatamente. O gerador também falha se `classification.toml` citar um comando que não existe no toolchain, para que a classificação não apodreça quando o Lean remover sintaxe.

Em tempo de execução, a Etapa A seleciona a allow-list pelo `lean-toolchain` **do projeto-alvo**. Sem arquivo para aquele toolchain, o resultado é `allowlist_unavailable` (fail-closed). Allow-list cujo conteúdo declara outro toolchain é rejeitada.

## Procedimento ao subir o toolchain

1. Atualizar `lean-toolchain` na raiz e nos fixtures (o teste `test_fixture_toolchain_matches_root` aponta cópias divergentes).
2. Rodar `python tools/gen_allowlist/gen.py` e ler o diff do JSON gerado.
3. Para cada comando novo, aplicar o critério de `classification.toml` e classificá-lo. Na dúvida, fail-closed.
4. Atualizar a classificação, regenerar, e rodar a suíte inteira.
5. A mudança de classificação é mudança de política: exige revisão por alguém que não é o autor.

## Tabela de confusables (TR39)

`src/auditor/data/unicode/confusables-16.0.0.txt` é cópia versionada do Unicode TR39 16.0.0 (termos de uso no cabeçalho do arquivo). Atualizar a versão é mudança explícita: novo arquivo com a nova versão no nome, e o caminho atualizado em `stage_a.py`.

## Allow-list de projeto (Mathlib e outros)

Comandos definidos por um projeto ou por suas dependências (o Mathlib define `lemma`, `alias`, `assert_not_exists`, …) não estão na allow-list do core. Para auditar arquivos desse projeto:

1. No projeto já compilado (no Mathlib: `lake exe cache get`), rodar `auditor-gen-allowlist --project <dir>`. O gerador roda `lake build`, importa todos os módulos do próprio projeto, extrai os comandos e grava `<dir>/.auditor/allowlist.json` com o `env_pin` (`lean-toolchain` + `lake-manifest.json`).
2. Ler a lista `unclassified` do arquivo gerado: são os comandos novos do projeto. Enquanto estiverem ali, são fail-closed.
3. Classificar cada um em `<dir>/.auditor/classification.toml` (chaves `classification_version`, `allowed`, `syntax_extension`, `metaprogramming`), com o mesmo critério de `tools/gen_allowlist/classification.toml`. A classificação não pode citar comandos do core nem comandos inexistentes; o gerador recusa.
4. Regenerar. `--check` falha se o arquivo não corresponder ao ambiente atual.
5. Classificação é política: exige revisão por alguém que não é o autor.

Ao mudar o `lake-manifest.json` ou o `lean-toolchain`, a allow-list fica obsoleta e a Etapa A falha fechada (`allowlist_stale`) até ser regenerada.

**A allow-list do Mathlib é evidência da camada 2**, gerada no fork do mantenedor. Ela não bloqueia a camada 1, cujo requisito é o gerador testado contra um projeto Lake arbitrário (`tests/allowlist`). A Fase 0 não verifica a correção semântica da classificação, só a correspondência com o pino (L-16).

## Inspetor da Etapa B

O inspetor (`src/auditor/lean/Inspect.lean`) é compilado com o toolchain do projeto-alvo e guardado em cache (`%LOCALAPPDATA%\auditor\inspector` no Windows, `$XDG_CACHE_HOME/auditor` ou `~/.cache/auditor` nos demais; `AUDITOR_CACHE` sobrescreve). A chave do cache é o hash do fonte + toolchain, então qualquer mudança no inspetor gera um binário novo.

Ao mudar `Inspect.lean`, subir `inspectorVersion` e `INSPECTOR_VERSION` (`stage_b.py`) juntos; um teste trava a divergência.

O percurso de dependências espelha `Lean.CollectAxioms.collect` do toolchain fixado. Ao subir o toolchain:
1. comparar `src/lean/Lean/Util/CollectAxioms.lean` do novo toolchain com `directDeps` em `Inspect.lean`;
2. rodar `tests/stage_b`. Os testes comparam o inspetor com `#print axioms` e travam as convenções de que a atribuição depende.

## Convenção de nomes auxiliares de `native_decide`

A atribuição de `native_decide` à declaração dona depende da convenção `X._proof_N` do compilador (L-4). Ela está travada por testes de regressão em `tests/stage_b` (`test_05_owner_attribution`, `test_edges_where_auxiliary_owned_by_top_level_declaration`, `test_edges_private_declaration_reported_and_owned`). A subida do toolchain precisa passar por eles.
