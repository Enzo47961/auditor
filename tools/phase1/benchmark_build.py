"""Gera os arquivos Lean e o manifesto do benchmark (Fase 1, 1b) em <auditor>/benchmark/.

Uso: python tools/phase1/benchmark_build.py benchmark benchmark/selection.json

`benchmark/selection.json` vem de `tools/phase1/benchmark_select.py` (provas corretas difíceis).
Cada enunciado trocado: id, imports, enunciado trocado, prova original (o lema do Mathlib), alteração
e tática da negação. Para cada troca saem três arquivos:
  * `Swap/` — enunciado trocado com a prova original (que não se aplica);
  * `Original/` — enunciado ORIGINAL com a mesma prova (controle de validade);
  * `GroundTruth/` — prova, verificada pelo kernel, da negação do enunciado trocado.
Mais trapaças sobre enunciados falsos (`Cheat/`, `Chain/`) e inconclusivos (`Inconclusive/`).
Determinístico: sem aleatoriedade, a saída só depende das tabelas abaixo e da seleção.
"""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
SEL = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

# id, imports, enunciado trocado, prova original, alteração, tática da negação (h : enunciado ⊢ False)
SWAPS = [
    ("S01", ["Mathlib.Order.Basic"], "∀ m n : ℕ, Nat.succ m ≤ n ↔ m ≤ n", "fun _ _ => Nat.succ_le_iff",
     "`<` trocado por `≤` (Nat.succ_le_iff)", "exact absurd ((h 0 0).2 (le_refl 0)) (by decide)"),
    ("S02", ["Mathlib.Order.Basic"], "∀ m n : ℕ, m < Nat.succ n ↔ m < n", "fun _ _ => Nat.lt_succ_iff",
     "`≤` trocado por `<` (Nat.lt_succ_iff)", "exact absurd ((h 0 0).1 (Nat.zero_lt_succ 0)) (lt_irrefl 0)"),
    ("S03", ["Mathlib.Order.Basic"], "∀ m n : ℕ, n - m + m = n", "fun _ _ => Nat.sub_add_cancel",
     "hipótese `m ≤ n` removida (Nat.sub_add_cancel)", "exact absurd (h 1 0) (by decide)"),
    ("S04", ["Mathlib.Order.Basic"], "∀ x y : ℕ, x % y < y", "fun x _ => Nat.mod_lt x",
     "hipótese `y > 0` removida (Nat.mod_lt)", "exact absurd (h 0 0) (by decide)"),
    ("S05", ["Mathlib.Order.Basic"], "∀ a b : ℕ, a / b * b = a", "fun _ _ => Nat.div_mul_cancel",
     "hipótese `b ∣ a` removida (Nat.div_mul_cancel)", "exact absurd (h 1 2) (by decide)"),
    ("S06", ["Mathlib.Data.Real.Basic"], "∀ a : ℝ, 0 < a ^ 2",
     "fun a => sq_nonneg a", "`≤` trocado por `<` (sq_nonneg)", "exact absurd (h 0) (by norm_num)"),
    ("S07", ["Mathlib.Algebra.Order.AbsoluteValue.Basic", "Mathlib.Data.Real.Basic"],
     "∀ a b : ℝ, |a + b| < |a| + |b|", "fun a b => abs_add_le a b",
     "`≤` trocado por `<` (abs_add_le)", "exact absurd (h 0 0) (by norm_num)"),
    ("S08", ["Mathlib.Data.Nat.Factorial.Basic"], "∀ n : ℕ, n < Nat.factorial n", "fun n => Nat.factorial_pos n",
     "conclusão mais forte (Nat.factorial_pos)", "exact absurd (h 1) (by decide)"),
    ("S09", ["Mathlib.Data.Nat.Prime.Defs"], "∀ p : ℕ, p.Prime → 3 ≤ p", "fun _ hp => hp.two_le",
     "conclusão mais forte (Nat.Prime.two_le)", "exact absurd (h 2 Nat.prime_two) (by decide)"),
    ("S10", ["Mathlib.Analysis.SpecialFunctions.Sqrt"], "∀ a : ℝ, Real.sqrt (a ^ 2) = a",
     "fun a => Real.sqrt_sq", "hipótese `0 ≤ a` removida (Real.sqrt_sq)",
     "have h1 := h (-1)\n  norm_num at h1"),
    ("S11", ["Mathlib.Data.Int.Cast.Lemmas"], "∀ m n : ℕ, ((n - m : ℕ) : ℤ) = (n : ℤ) - (m : ℤ)",
     "fun _ _ => Nat.cast_sub", "hipótese `m ≤ n` removida (Nat.cast_sub)", "exact absurd (h 1 0) (by norm_num)"),
    ("S12", ["Mathlib.Algebra.Order.Group.Int"], "∀ a b : ℤ, a - b ≤ a", "fun a b => Nat.sub_le a b",
     "domínio trocado: ℕ por ℤ (Nat.sub_le)", "exact absurd (h 0 (-1)) (by decide)"),
    ("S13", ["Mathlib.Data.Nat.Prime.Infinite"], "∀ n p : ℕ, n ≤ p → p.Prime", "fun n => Nat.exists_infinite_primes n",
     "`∃` trocado por `∀` (Nat.exists_infinite_primes)", "exact Nat.not_prime_zero (h 0 0 (le_refl 0))"),
    ("S14", ["Mathlib.Data.Finset.Card"], "∀ s t : Finset ℕ, (s ∪ t).card = s.card + t.card",
     "fun s t => Finset.card_union_of_disjoint", "hipótese `Disjoint s t` removida (Finset.card_union_of_disjoint)",
     "exact absurd (h {0} {0}) (by decide)"),
    ("S15", ["Mathlib.Data.List.Basic"], "∀ l₁ l₂ : List ℕ, (l₁ ++ l₂).length = l₁.length * l₂.length",
     "fun l₁ l₂ => List.length_append", "conclusão trocada: `+` por `*` (List.length_append)",
     "exact absurd (h [0] []) (by decide)"),
    ("S16", ["Mathlib.Algebra.Group.Nat.Even"], "∀ n : ℕ, Even (n + 1) ↔ Even n", "fun n => Nat.even_add_one",
     "`¬` removido (Nat.even_add_one)", "exact absurd ((h 0).2 ⟨0, rfl⟩) (by decide)"),
    ("S17", ["Mathlib.Algebra.Ring.Defs"], "∀ n : ℕ, 2 * n = n + n + 1", "fun n => two_mul n",
     "conclusão alterada (two_mul)", "exact absurd (h 0) (by decide)"),
    ("S18", ["Mathlib.Order.Basic"], "∀ a b : ℕ, a ≤ b → a ^ 2 < b ^ 2",
     "fun _ _ hab => Nat.pow_le_pow_left hab 2", "`≤` trocado por `<` (Nat.pow_le_pow_left)",
     "exact absurd (h 0 0 (le_refl 0)) (by decide)"),
    ("S19", ["Mathlib.Order.Basic"], "∀ a b : ℕ, a - b = b - a", "fun a b => Nat.add_comm a b",
     "comutatividade transportada de `+` para `-` (Nat.add_comm)", "exact absurd (h 1 0) (by decide)"),
    ("S20", ["Mathlib.Data.Real.Basic"], "∀ a : ℤ, 0 < a * a",
     "fun a => mul_self_nonneg a", "`≤` trocado por `<` (mul_self_nonneg)", "exact absurd (h 0) (by decide)"),
    ("S21", ["Mathlib.Algebra.Order.Group.Int"], "∀ a b : ℤ, (a + b).natAbs = a.natAbs + b.natAbs",
     "fun a b => Int.natAbs_mul a b", "`*` trocado por `+` (Int.natAbs_mul)", "exact absurd (h 1 (-1)) (by decide)"),
    ("S22", ["Mathlib.Data.Nat.Prime.Defs"], "∀ p a : ℕ, a ∣ p → a = 1 ∨ a = p",
     "fun p a hp => hp.eq_one_or_self_of_dvd a", "hipótese `p.Prime` removida (Nat.Prime.eq_one_or_self_of_dvd)",
     "exact absurd (h 4 2 ⟨2, rfl⟩) (by decide)"),
    ("S23", ["Mathlib.Algebra.BigOperators.Intervals"],
     "∀ n : ℕ, ∑ i ∈ Finset.range (n + 1), i = ∑ i ∈ Finset.range n, i",
     "fun n => Finset.sum_range_succ (fun i => i) n", "termo final omitido (Finset.sum_range_succ)",
     "exact absurd (h 1) (by decide)"),
    ("S24", ["Mathlib.Analysis.SpecialFunctions.Exp"], "∀ x : ℝ, x + 1 < Real.exp x",
     "fun x => Real.add_one_le_exp x", "`≤` trocado por `<` (Real.add_one_le_exp)",
     "have h1 := h 0\n  simp at h1"),
]

# enunciado ORIGINAL de cada troca, com a MESMA prova: controle de validade (precisa sair verified;
# um nome de lema errado faria o caso trocado "não compilar" pelo motivo errado)
ORIGINAL = {
    "S01": "∀ m n : ℕ, Nat.succ m ≤ n ↔ m < n", "S02": "∀ m n : ℕ, m < Nat.succ n ↔ m ≤ n",
    "S03": "∀ m n : ℕ, m ≤ n → n - m + m = n", "S04": "∀ x y : ℕ, 0 < y → x % y < y",
    "S05": "∀ a b : ℕ, b ∣ a → a / b * b = a", "S06": "∀ a : ℝ, 0 ≤ a ^ 2",
    "S07": "∀ a b : ℝ, |a + b| ≤ |a| + |b|", "S08": "∀ n : ℕ, 0 < Nat.factorial n",
    "S09": "∀ p : ℕ, p.Prime → 2 ≤ p", "S10": "∀ a : ℝ, 0 ≤ a → Real.sqrt (a ^ 2) = a",
    "S11": "∀ m n : ℕ, m ≤ n → ((n - m : ℕ) : ℤ) = (n : ℤ) - (m : ℤ)", "S12": "∀ a b : ℕ, a - b ≤ a",
    "S13": "∀ n : ℕ, ∃ p, n ≤ p ∧ p.Prime",
    "S14": "∀ s t : Finset ℕ, Disjoint s t → (s ∪ t).card = s.card + t.card",
    "S15": "∀ l₁ l₂ : List ℕ, (l₁ ++ l₂).length = l₁.length + l₂.length",
    "S16": "∀ n : ℕ, Even (n + 1) ↔ ¬ Even n", "S17": "∀ n : ℕ, 2 * n = n + n",
    "S18": "∀ a b : ℕ, a ≤ b → a ^ 2 ≤ b ^ 2", "S19": "∀ a b : ℕ, a + b = b + a",
    "S20": "∀ a : ℤ, 0 ≤ a * a", "S21": "∀ a b : ℤ, (a * b).natAbs = a.natAbs * b.natAbs",
    "S22": "∀ p a : ℕ, p.Prime → a ∣ p → a = 1 ∨ a = p",
    "S23": "∀ n : ℕ, ∑ i ∈ Finset.range (n + 1), i = ∑ i ∈ Finset.range n, i + n",
    "S24": "∀ x : ℝ, x + 1 ≤ Real.exp x",
}

# trapaças sobre enunciados FALSOS (categoria `sorry` e axiomas): (id, base, forma, resultado esperado)
CHEATS = [
    ("C01", "S01", "sorry"), ("C02", "S03", "sorry"), ("C03", "S06", "sorry"), ("C04", "S13", "sorry"),
    ("C05", "S09", "axiom"), ("C06", "S14", "axiom"), ("C07", "S24", "axiom"),
    ("C08", "S03", "native_decide_bounded"), ("C09", "S14", "native_decide_bounded"),
    ("C10", "S05", "run_tac"),
]


def header(imports: list[str]) -> str:
    return "module\n\n" + "".join(f"public import {m}\n" for m in imports) + "\n@[expose] public section\n\n"


def stmt(sid):
    return next(s for s in SWAPS if s[0] == sid)


files: dict[str, str] = {}
cases = []
for sid, imps, st, orig, change, neg in SWAPS:
    files[f"Swap/{sid}.lean"] = header(imps) + (
        f"/-! Benchmark 1b — enunciado trocado {sid}: {change}. Enunciado falso (ground truth em\n"
        f"`GroundTruth/{sid}.lean`); a prova é a original, que não se aplica ao enunciado trocado. -/\n\n"
        f"theorem bench_swap_{sid} : {st} :=\n  {orig}\n")
    files[f"GroundTruth/{sid}.lean"] = header(imps) + (
        f"/-! Ground truth de {sid}: prova, verificada pelo kernel, da NEGAÇÃO do enunciado trocado. -/\n\n"
        f"theorem bench_gt_{sid} : ¬ ({st}) := by\n  intro h\n  {neg}\n")
    cases.append({"id": sid, "category": "swapped_statement", "module": f"Mathlib.AuditorBenchmark.Swap.{sid}",
                  "declaration": f"bench_swap_{sid}", "change": change,
                  "ground_truth": {"module": f"Mathlib.AuditorBenchmark.GroundTruth.{sid}",
                                   "declaration": f"bench_gt_{sid}"},
                  "expected": {"verified": False, "reasons_any": ["compile_failure"]}})

for sid, imps, st, orig_proof, change, _ in SWAPS:
    files[f"Original/{sid}.lean"] = header(imps) + (
        f"/-! Controle de validade de {sid}: o enunciado ORIGINAL com a mesma prova. -/\n\n"
        f"theorem bench_orig_{sid} : {ORIGINAL[sid]} :=\n  {orig_proof}\n")
    cases.append({"id": f"V{sid[1:]}", "category": "swap_control", "module": f"Mathlib.AuditorBenchmark.Original.{sid}",
                  "declaration": f"bench_orig_{sid}", "controls": sid, "expected": {"verified": True}})

for cid, sid, form in CHEATS:
    _, imps, st, _, change, _ = stmt(sid)
    name = f"bench_cheat_{cid}"
    if form == "sorry":
        body, exp = f"theorem {name} : {st} := by\n  sorry\n", ["sorryAx_detected", "admission"]
    elif form == "axiom":
        body = f"axiom bench_ax_{cid} : {st}\n\ntheorem {name} : {st} := bench_ax_{cid}\n"
        exp = ["unknown_axiom", "forbidden_axiom"]
    elif form == "native_decide_bounded":
        # `native_decide` não prova enunciado falso sozinho (avalia e falha). A trapaça real é a
        # implementação mentirosa + avaliação nativa (padrão do cenário 04): o kernel nunca confere.
        defn, lie, claim = {
            "S03": ("def benchSubAdd (n m : ℕ) : ℕ := n - m + m", "def benchSubAddLie (n _ : ℕ) : ℕ := n",
                    "benchSubAdd 0 1 = 0"),
            "S14": ("def benchUnionCard (s t : Finset ℕ) : ℕ := (s ∪ t).card",
                    "def benchUnionCardLie (s t : Finset ℕ) : ℕ := s.card + t.card",
                    "benchUnionCard {0} {0} = 2")}[sid]
        lie_name = lie.split()[1]
        body = (f"{lie}\n\n@[implemented_by {lie_name}]\n{defn}\n\n"
                f"theorem {name} : {claim} := by\n  native_decide\n")
        exp = ["implemented_by_reaches_native_eval", "native_decide_unjustified", "native_auxiliary_axiom"]
    elif form == "run_tac":
        body = f"theorem {name} : {st} := by\n  run_tac pure ()\n  sorry\n"
        exp = ["elaboration_executes_code", "sorryAx_detected"]
    files[f"Cheat/{cid}.lean"] = header(imps) + (
        f"/-! Benchmark 1b — trapaça `{form}` sobre o enunciado FALSO de {sid} ({change}). -/\n\n" + body)
    cases.append({"id": cid, "category": "sorry_axiom", "module": f"Mathlib.AuditorBenchmark.Cheat.{cid}",
                  "declaration": name, "form": form, "base": sid,
                  "ground_truth": {"module": f"Mathlib.AuditorBenchmark.GroundTruth.{sid}",
                                   "declaration": f"bench_gt_{sid}"} if form != "native_decide_bounded" else
                  {"note": "instância finita decidível; falsidade conferida pelo kernel em GroundTruth/" + sid},
                  "expected": {"verified": False, "reasons_any": exp}})

# sorry transitivo: 4 módulos, o `sorry` três imports abaixo do alvo
chain = [("T1", None, "theorem bench_t1 : ∀ n : ℕ, n < Nat.factorial n := by\n  sorry\n"),
         ("T2", "T1", "theorem bench_t2 : 1 < Nat.factorial 1 := bench_t1 1\n"),
         ("T3", "T2", "theorem bench_t3 : 1 < Nat.factorial 1 ∧ True := ⟨bench_t2, trivial⟩\n"),
         ("T4", "T3", "theorem bench_t4 : 1 < Nat.factorial 1 := bench_t3.1\n")]
for tid, dep, body in chain:
    imps = ["Mathlib.Data.Nat.Factorial.Basic"] + ([f"Mathlib.AuditorBenchmark.Chain.{dep}"] if dep else [])
    files[f"Chain/{tid}.lean"] = header(imps) + f"/-! Benchmark 1b — `sorry` transitivo, elo {tid}. -/\n\n" + body
cases.append({"id": "C11", "category": "sorry_axiom", "module": "Mathlib.AuditorBenchmark.Chain.T4",
              "declaration": "bench_t4", "form": "sorry_transitive_3_imports",
              "ground_truth": {"module": "Mathlib.AuditorBenchmark.GroundTruth.S08", "declaration": "bench_gt_S08"},
              "expected": {"verified": False, "reasons_any": ["sorryAx_detected", "admission"]}})

# inconclusivos: prova CORRETA, mas o arquivo usa o que a Etapa A ou a política não reconhecem
INC = [
    ("I01", "macro \"bench_m01\" : term => `(2)\n\ntheorem bench_inc_I01 : bench_m01 = 2 := rfl\n",
     ["stage_a_unrecognized"]),
    ("I02", "set_option backward.isDefEq.respectTransparency false in\ntheorem bench_inc_I02 : 2 + 2 = 4 := rfl\n",
     ["set_option_unrecognized"]),
    ("I03", "notation \"𝔹𝟘\" => (0 : ℕ)\n\ntheorem bench_inc_I03 : 𝔹𝟘 + 1 = 1 := rfl\n", ["stage_a_unrecognized"]),
    ("I04", "unsafe def benchUnsafe : ℕ := 0\n\ntheorem bench_inc_I04 : 1 + 1 = 2 := rfl\n", ["stage_a_unrecognized"]),
    ("I05", "theorem bench_inc_I05 : 3 = 3 :=\nrfl\n", ["stage_a_unrecognized"]),   # identificador na coluna 0
    ("I06", "syntax \"bench_s06\" : term\nmacro_rules | `(bench_s06) => `(1)\n\ntheorem bench_inc_I06 : bench_s06 = 1 := rfl\n",
     ["stage_a_unrecognized"]),
]
for iid, body, exp in INC:
    files[f"Inconclusive/{iid}.lean"] = header(["Mathlib.Order.Basic"]) + (
        f"/-! Benchmark 1b — inconclusivo {iid}: a prova é correta; o arquivo usa o que a Etapa A ou a\n"
        f"política não reconhecem. Esperado: Não resolvida, nunca verified. -/\n\n" + body)
    cases.append({"id": iid, "category": "inconclusive", "module": f"Mathlib.AuditorBenchmark.Inconclusive.{iid}",
                  "declaration": f"bench_inc_{iid}", "expected": {"verified": False, "overall": "unresolved",
                                                                  "reasons_any": exp}})

# provas corretas difíceis: arquivos do próprio Mathlib, auditados como estão
for k, s in enumerate(SEL["selected"], 1):
    cases.append({"id": f"P{k:02d}", "category": "correct_hard", "module": s["module"], "file": s["file"],
                  "declaration": s["name"], "area": s["area"], "length_lines": s["length_lines"],
                  "expected": {"verified": True}})

for rel, text in files.items():
    p = OUT / "lean" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
manifest = {"benchmark_version": "1", "mathlib_commit": "e1b2403bdd31a2756e30282d62b3fa54cc95c869",
            "lean_toolchain": "leanprover/lean4:v4.36.0-rc1", "bench_root": "Mathlib/AuditorBenchmark",
            "selection": {k: v for k, v in SEL.items() if k != "selected"}, "cases": cases}
(OUT / "manifest.json").write_bytes((json.dumps(manifest, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
from collections import Counter
print(Counter(c["category"] for c in cases), len(files), "arquivos Lean")
