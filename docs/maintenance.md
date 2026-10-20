# Manutenção da allow-list da Etapa A

## O que é mantido e por quem

A allow-list tem duas partes de origem diferente:

| Parte | Origem | Arquivo |
|---|---|---|
| Lista de comandos | **extraída mecanicamente** do toolchain (categoria `command` do parser, via `tools/gen_allowlist/Dump.lean`) | gerada em `src/auditor/data/allowlist/<toolchain>.json` |
| Classificação de risco (`syntax_extension`, `metaprogramming`) e tokens de continuação | **mantida à mão**, com critério escrito | `tools/gen_allowlist/classification.toml` |

Comando extraído que não está classificado cai em `allowed`. Por isso, **ao subir o toolchain, todo comando novo precisa de revisão humana**: o gerador lista o que mudou, mas não julga o risco.

## Teste de defasagem

`tests/maintenance/test_allowlist_fresh.py` roda `gen.py --check`: recompila o extrator contra o `lean-toolchain` fixado e falha se o arquivo versionado não corresponder exatamente. O gerador também falha se `classification.toml` citar um comando que não existe no toolchain, para que a classificação não apodreça quando o Lean remover sintaxe.

Em tempo de execução, a Etapa A seleciona a allow-list pelo `lean-toolchain` **do projeto-alvo**. Sem arquivo para aquele toolchain, o resultado é `allowlist_unavailable` (fail-closed). Allow-list cujo conteúdo declara outro toolchain é rejeitada.

## Procedimento ao subir o toolchain

1. Atualizar `lean-toolchain` na raiz e nos fixtures (o teste `test_fixture_toolchain_matches_root` aponta cópias divergentes).
2. Rodar `python tools/gen_allowlist/gen.py` e ler o diff do JSON gerado.
3. Para cada comando novo, aplicar o critério de `classification.toml` e classificá-lo. Na dúvida, fail-closed.
4. Atualizar a classificação, regenerar, e rodar a suíte inteira.
5. A mudança de classificação é mudança de política: exige revisão por alguém que não é o autor.

## Tabela de confusables (TR39)

`src/auditor/data/unicode/confusables-16.0.0.txt` é cópia versionada do Unicode TR39 16.0.0 (termos de uso no cabeçalho do arquivo). Atualizar a versão é mudança explícita: novo arquivo com a nova versão no nome, e o caminho atualizado em `stage_a.py`.

## Convenção de nomes auxiliares de `native_decide`

A atribuição de `native_decide` à declaração dona depende da convenção `X._proof_N` do compilador (L-4). Quando a Etapa B existir, ela terá teste de regressão próprio contra o toolchain fixado; a subida do toolchain precisa passar por ele.
