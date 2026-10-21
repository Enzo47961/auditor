# Roadmap

**A Fase 1 não começa antes da camada 2 da Fase 0 estar medida.** O critério de go/no-go da Fase 0 é a camada 2 (GitHub Actions em PRs reais do fork do Mathlib), não a camada 1. Ver o README, seção "Status", e o roteiro em `docs/ci.md`.

## Fase 1 — itens já decididos

| Item | Origem | Decisão |
|---|---|---|
| Hash de declaração resistente a colisão | D-18, instrução 11 | Substituir o hash estrutural de 64 bits (`Expr.hash`) em `declaration_hash` por SHA-256 truncado a 128 bits ou BLAKE3-128, calculado sobre uma serialização canônica do tipo e do valor. 64 bits não resiste a colisão adversarial: quem forja uma colisão troca uma declaração sem mudar o hash. Aceito na Fase 0 só porque ainda não há alvo adversário (L-14). |
| Revogação de selos | `docs/invalidation.md` | Implementar o modelo: selos imutáveis, eventos append-only, estado derivado, propagação. |
| `depends_on` completo | `docs/invalidation.md` | Fecho de dependências locais emitido pelo inspetor, para a propagação de revogação. |
| Timeout por arquivo medido | D-21, instrução 11 | Reajustar o default de 90 s pelo p95 por arquivo medido na camada 2 (`tools/layer2/timings.py`), não por intuição. |
| Toolchain Lean e dependências Python verificados por hash | L-18, D-35, instrução 12 | O CI só confere por hash as actions e o elan. O toolchain Lean (baixado pelo elan a partir de `lean-toolchain`) e as dependências Python (resolvidas pelo pip) passam a ser conferidos também: SHA-256 da release do toolchain fixado contra um valor versionado no repositório, e `pip install --require-hashes` com um arquivo de requisitos com hashes (incluindo o fecho de `jsonschema`). Sem isso, quem compromete o toolchain do Lean ou um pacote PyPI compromete o auditor inteiro — e o auditor é o que detecta comprometimento. |
