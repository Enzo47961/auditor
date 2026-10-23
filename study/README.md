# Estudo de usuário (sub-fase 1c): dados

Metodologia: `docs/user-study.md`. Convite: `docs/user-study-invite.md`.

| Arquivo | Conteúdo | Gerado por |
|---|---|---|
| `selection.json` | os 31 PRs integrados depois de `e1b2403b`, critérios aplicados, os 13 elegíveis e os estratos | `tools/phase1/study_select.py` |
| `patches/` | os diffs dos PRs, aplicáveis sobre `e1b2403b` | `tools/phase1/study_select.py` |
| `audit.json` | a auditoria de cada PR elegível e a exclusão (B) por PR (run 39936018705); substituída pela exclusão por declaração (instrução 28) | `tools/phase1/study_audit.py` |
| `defects.json`, `defects/` | os defeitos plantados (instruções 27 e 28): diff só do defeito, ground truth, resultado esperado | conferidos por `tools/phase1/study_audit.py --defects` (`auditor-study`, modo `defects`) |

## Defeitos plantados: como conferir

```
python tools/phase1/study_audit.py <mathlib em e1b2403b> --selection study/selection.json \
    --patches study/patches --policy policy.toml --out out/ --defects study/defects.json
```

Para cada defeito, a ferramenta aplica o patch do PR e o do defeito, audita os arquivos e confere três coisas:
- a declaração esperada sai com o estado esperado;
- a razão é a esperada;
- a razão **não** é de causa conhecida (`ctorIdx`, `backward.*`, `target_defines_executable_code`).

Se a compilação falhar, guarda o log do Lean (o relatório do auditor não traz a mensagem). Conferência aprovada: run 39973055204.

## Lição (defeito B, instrução 29)

**Fixtures de defeito plantado reusam a forma do benchmark C08 (implementação própria); tentar inventar a partir do zero introduz erro de compilação que mascara o defeito.**

A primeira versão do defeito B usou `@[implemented_by Nat.add]`. O Lean rejeita esse alvo ("Invalid `implemented_by` argument"). Sem a troca, o `native_decide` avaliou o valor verdadeiro (`2 * 3 = 6`) e recusou a proposição. O auditor viu só `compile_failure`, não o defeito (run 39971602437). A correção usa uma implementação própria (`private def iInterIndexImpl (a b : ℕ) : ℕ := a + b`), na forma do C08 (`benchmark/lean/Cheat/C08.lean`).
