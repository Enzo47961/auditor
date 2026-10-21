"""Catálogo de mutações (docs/maintenance.md, "Testes de mutação").

Cada mutação quebra deliberadamente uma checagem. A suíte do grupo precisa FALHAR com ela
aplicada; se passar, a mutação "sobreviveu" e há um buraco nos testes. Os padrões são
strings raw e precisam ocorrer exatamente uma vez no arquivo (um teste trava isso, para o
catálogo não apodrecer quando o código muda).

Formato: GRUPOS = {grupo: {"tests": [...], "mutations": [(arquivo, original, mutado), ...]}}
"""

SA = "src/auditor/tier1/stage_a.py"
AL = "src/auditor/allowlist.py"
INS = "src/auditor/lean/Inspect.lean"
SB = "src/auditor/tier1/stage_b.py"
AG = "src/auditor/aggregator.py"
PO = "src/auditor/policy/__init__.py"
RP = "src/auditor/report.py"
TB = "src/auditor/tcb_boundary.py"
FP = "src/auditor/fingerprint/__init__.py"
PD = "src/auditor/pydeps.py"
CI = "src/auditor/ci.py"
GT = "tools/gen_tcb_roots.py"

GROUPS = {
    "stage_a": {
        "tests": ["tests/stage_a"],
        "mutations": [
            (SA, r"if cp in BIDI_CONTROLS or cp in ZERO_WIDTH:", r"if cp in BIDI_CONTROLS:"),
            (SA, r'if t.text in ("sorry", "admit"):', r'if t.text in ("admit",):'),
            (SA, r'elif t.text == "native_decide":', r"elif False:"),
            (SA, r'scoped = n3 is not None and n3.kind == "ident" and n3.text == "in"', r"scoped = False"),
            (SA, r"            if word in risky_syntax:", r"            if False:"),
            (SA, r"            elif word in risky_meta:", r"            elif False:"),
            (SA, r'res.unrecognized.append(Item("unknown_command"', r'res.warnings.append(Item("unknown_command"'),
            # instrução 12 (D-41): unlock_limits = os três set_option … 0
            (SA, r'        elif t.text == "unlock_limits":', r"        elif False:"),
            (SA, "                and toks[k + 1].text == \"in\":\n            k += 2",
             "                and toks[k + 1].text == \"in\":\n            k += 1"),
            # camada 2, instrução 16: `module` de cabeçalho (D-57); comandos-símbolo só no início (D-56)
            (SA, r'header_module = k == 0 and t.kind == "ident" and not t.quoted and t.text == "module"',
             r'header_module = t.kind == "ident" and not t.quoted and t.text == "module"'),
            (SA, r'header_module = k == 0 and t.kind == "ident" and not t.quoted and t.text == "module"',
             r"header_module = False"),
            (SA, '        if (t.kind in ("ident", "hashcmd") and not t.quoted) or \\',
             '        if (t.kind in ("ident", "hashcmd", "symbol") and not t.quoted) or \\'),
            (SA, r'                (at_command_start and t.kind in ("ident", "symbol")):', r"                False:"),
        ],
    },
    "allowlist": {
        "tests": ["tests/allowlist"],
        "mutations": [
            (SA, r'if data.get("env_pin") != env_pin(toolchain, manifest.read_bytes()):', r"if False:"),
            (SA, r'if data.get("kind") != "project":', r"if False:"),
            (SA, r"elif word in unclassified:", r"elif False:"),
            (AL, r'"unclassified": sorted(new - classified),', r'"unclassified": [],'),
            (AL, r"stale = set(listed) - new", r"stale = set()"),
            (AL, r'for part in (f"auditor-env-pin-v{ENV_PIN_VERSION}".encode(), toolchain.encode("utf-8"), manifest):',
             r'for part in (f"auditor-env-pin-v{ENV_PIN_VERSION}".encode(), toolchain.encode("utf-8")):'),
            (AL, r"        if dup:", r"        if False:"),
            (AL, r"        if unknown_keys:", r"        if False:"),
            (AL, r"if not tc_file.is_file() or not manifest.is_file():", r"if not tc_file.is_file():"),
            # camada 2, instrução 15: só as bibliotecas-alvo (D-52); fim de linha (D-53)
            (AL, r'    mods = [m for m in mods if any(m == r or m.startswith(r + ".") for r in libs)]', r"    mods = mods"),
            (AL, r'        libs = [t for t in data.get("defaultTargets", []) if t in names]',
             r'        libs = list(data.get("defaultTargets", []))'),
            (AL, r"    if not libs:", r"    if False:"),
            (AL, r"    manifest = normalize_newlines(manifest)", r"    manifest = manifest"),
            # instrução 18: declaração de revisão da classificação (L-26); hash da classificação (D-53)
            (AL, r"        if reviewed_by not in REVIEW_STATUSES:", r"        if False:"),
            (AL, r'        if cls.get("reviewer_independence") != REVIEW_STATUSES[reviewed_by]:', r"        if False:"),
            (AL, r'        "classification_review": {k: cls.get(k) for k in REVIEW_KEYS} if cls_sha else None,',
             r'        "classification_review": None,'),
            (AL, r"        raw = normalize_newlines(cls_path.read_bytes())", r"        raw = cls_path.read_bytes()"),
            (SA, r'    return review.get("reviewed_by") or "undeclared"', r'    return "author-self-review"'),
            (SA, r'    if allow.get("kind") != "project":' + "\n" + r'        return "core-only"',
             r'    if False:' + "\n" + r'        return "core-only"'),
        ],
    },
    "stage_b": {
        "tests": ["tests/stage_b"],
        "mutations": [
            (INS, r"  | .inductInfo v   => v.type.getUsedConstants ++ v.ctors.toArray",
             r"  | .inductInfo v   => v.type.getUsedConstants"),
            (INS, "    | .str p _ => ownerOf env p\n", "    | .str _ _ => none\n"),
            (INS, "  match privateToUserName? n with\n  | some u => !u.isAnonymous && !u.isInternalDetail\n"
                  "  | none => !n.isInternalDetail", "  !n.isInternalDetail"),
            (INS, "    if (declRangeExt.find? (level := .server) env n).isNone then continue\n", ""),
            (SB, r'if sorted(d["axioms_official"]) != sorted(d["axioms_closure"]):', r"if False:"),
            (SB, r'        if d["missing"]:', r"        if False:"),
            (SB, r'                if r["owner"] is None:', r"                if False:"),
            (SB, r'    if facts.get("lean_version") != expected_version:', r"    if False:"),
            (SB, r'res.build = {"status": "timeout"', r'res.build = {"status": "success"'),
            (SB, r'res.build["cycle_detected"] = "build cycle detected" in log', r'res.build["cycle_detected"] = False'),
            (SB, r"if not parts or not all(MODULE_COMPONENT.match(p) for p in parts):", r"if not parts:"),
            (SB, '    if b.returncode != 0:\n        res.build["cycle_detected"]',
             '    if False:\n        res.build["cycle_detected"]'),
            (SB, r'                if e["level"] == tb.UNRESOLVED:', r"                if False:"),
            # instrução 12: inspetor v4 (D-39, D-43)
            (INS, '.str (.str (.str _ "_native") tac) last', '.str (.str (.str _ "_nativeX") tac) last'),
            (INS, "importModules #[{module := mod}] {} (loadExts := false)",
             "importModules #[{module := mod}] {} (loadExts := true)"),
            (INS, "  | .axiomInfo v    => v.type.getUsedConstants\n", "  | .axiomInfo _    => #[]\n"),
            (SB, r'        if not isinstance(d.get("native_auxiliary"), list):', r"        if False:"),
        ],
    },
    "policy": {
        "tests": ["tests/policy", "tests/tcb", "tests/cli", "tests/fail-closed/test_fail_closed.py",
                  "tests/maintenance/test_no_llm.py",
                  "tests/conformance/test_01_sorry_target.py", "tests/conformance/test_02_sorry_transitive.py",
                  "tests/conformance/test_03_axiom_unknown.py", "tests/conformance/test_04_implemented_by.py",
                  "tests/conformance/test_04b_extern.py", "tests/conformance/test_05_native_decide.py",
                  "tests/conformance/test_06_tcb_boundary.py"],
        "mutations": [
            (AG, "        if ax in policy.admissions:\n            origins", "        if False:\n            origins"),
            (AG, r'if policy.unknown_axiom_action == "fail_closed":', r"if False:"),
            (AG, r'effects.append(M("nonconforming", "forbidden_axiom"', r'effects.append(M("unresolved", "forbidden_axiom"'),
            (AG, r'        if j.status == "absent":', r"        if False:"),
            (AG, r'        elif j.status == "malformed":', r"        elif False:"),
            (AG, r"if owner is None or owner not in owner_docs:", r"if owner is None:"),
            (AG, "        if native:\n            code", "        if False:\n            code"),
            (AG, r'user = sorted(e["name"] for e in entries if e.get("level") == "user")',
             r'user = sorted(e["name"] for e in entries if e.get("level") in ("user", "tcb"))'),
            (AG, r"        if unresolved:", r"        if False:"),
            (AG, '    if d["name"] in owned:\n        return []', '    if True:\n        return []'),
            (AG, r"        if (opt, val) in policy.forbidden_options:", r"        if False:"),
            (AG, r'return j.status == "valid" and j.reason == policy.exemption_reason', r'return j.status == "valid"'),
            (AG, r"    if not any(file_rel == p or", r"    if False and not any(file_rel == p or"),
            (AG, r"        elif not policy.option_recognized(opt):", r"        elif False:"),
            (AG, r'    if proof == "Rejeitada" or premises == "Não conforme":', r'    if proof == "Rejeitada":'),
            (AG, r'ps, pr = worst("proof", ("rejected", "unresolved"))', r'ps, pr = worst("proof", ("unresolved", "rejected"))'),
            (AG, r"    if not ctx.tcb_complete:", r"    if False:"),
            (AG, r"                if line is None or line > f.line:", r"                if True:"),
            (AG, r"    content = [u for u in sa.unrecognized if u.code not in STAGE_A_INFRA]", r"    content = []"),
            (PO, r"    if len(lines) > 1:", r"    if False:"),
            (PO, r'reason="([^"\\\r\n]+)"', r'reason="([^"\r\n]+)"'),
            (PO, r'    if ax["unknown_axiom_action"] == "allow_with_warning" and not', r"    if False and not"),
            (PO, r"            if n in seen:", r"            if False:"),
            (RP, r"    elif file_unrecognized or any(", r"    elif any("),
            (RP, "    if infra:\n        code = 2", "    if False:\n        code = 2"),
            (RP, r"            if n not in seen:", r"            if False:"),
            (RP, "            if allow_empty:\n                empty_allowed = True",
             "            if True:\n                empty_allowed = True"),
            (TB, r"        if any((r / rel).exists() for r in b.user_roots):", r"        if False:"),
            (TB, r'        if module.split(".")[0] not in b.trusted_roots:', r"        if False:"),
            (TB, r"        if _norm(p) != _norm(b.toolchain_lib / rel):", r"        if False:"),
            (FP, r"        if not isinstance(v, dict) or any(not v.get(k) for k in keys):",
             r"        if not isinstance(v, dict):"),
            (PD, "            if has_marker:\n                continue\n            raise DependencyError",
             "            if True:\n                continue\n            raise DependencyError"),
            (PD, r'            if "extra" in marker:', r"            if True:"),
            # instrução 12: axioma auxiliar nativo (D-43)
            (AG, r"        elif ax in aux:", r"        elif False:"),
            (AG, "        {a[\"axiom\"] for a in d.get(\"native_auxiliary\", [])}", "        set()"),
            (PO, r'    if ax["native_auxiliary_action"] not in NATIVE_AUXILIARY_ACTIONS:', r"    if False:"),
            # instrução 13: target_trusted_roots (D-42, D-47..D-49); uma mutação por raiz
            (TB, r'    roots = frozenset(trusted["roots"])', r'    roots = frozenset(trusted["roots"]) - {"Init"}'),
            (TB, r'    roots = frozenset(trusted["roots"])', r'    roots = frozenset(trusted["roots"]) - {"Lean"}'),
            (TB, r'    roots = frozenset(trusted["roots"])', r'    roots = frozenset(trusted["roots"]) - {"Std"}'),
            (TB, r'    roots = frozenset(trusted["roots"])', r'    roots = frozenset(trusted["roots"]) - {"Lake"}'),
            (TB, r'    roots = frozenset(trusted["roots"])', r"    roots = declared"),
            (TB, r'        if module.split(".")[0] not in b.declared_roots:', r"        if False:"),
            (TB, r'    if sorted(declared) != sorted(trusted["declared_by_toolchain"]):', r"    if False:"),
            (TB, r"    if not roots <= declared:", r"    if False:"),
            (TB, r'    if data.get("toolchain") != toolchain:', r"    if False:"),
        ],
    },
    "ci": {
        "tests": ["tests/ci"],
        "mutations": [
            (CI, r"        if remaining < MIN_SLICE_S:", r"        if False:"),
            (CI, r'    infra = [r for r in results if r["status"] in INFRA_STATUSES]',
             r'    infra = [r for r in results if r["status"] in ("infra",)]'),
            (CI, r'        return outcome["exit_code"]', r'        return 1 if outcome["audit_failed"] else 0'),
            (CI, r'        "exit_code": 2 if infra else 1 if failed else 0,', r'        "exit_code": 1 if failed else 2 if infra else 0,'),
            (CI, r'    if conclusion not in ("success", "failure"):', r"    if False:"),
            (CI, '            or not isinstance(data.get("infra_failed"), bool) \\', "            or False \\"),
            (CI, r'            or not isinstance(data.get("cache_cold_extension"), bool):', r"            or False:"),
            (CI, '    if data["infra_failed"]:\n        return LABEL, "infra_failed"', '    if False:\n        return LABEL, "infra_failed"'),
            (CI, '    if data["cache_cold_extension"]:\n        return LABEL_FIRST_RUN', '    if False:\n        return LABEL_FIRST_RUN'),
            (CI, '        return LABEL, "outcome ausente"', '        return None, "outcome ausente"'),
            (CI, r'            entry["status"] = {0: "pass", 1: "fail", 2: "infra"}.get(entry["exit_code"], "infra")',
             r'            entry["status"] = {0: "pass", 1: "fail", 2: "pass"}.get(entry["exit_code"], "pass")'),
            # instrução 11: timeout por arquivo (D-21), relógio e cache_state (D-28)
            (CI, r'        if entry["status"] is None and "timeout" in entry.get("infra_reasons", []):', r"        if False:"),
            (CI, r"            aborted = True", r"            pass"),
            (CI, r"        if aborted:", r"        if False:"),
            (CI, r"        limit = min(timeout_file_s, remaining)", r"        limit = remaining"),
            (CI, r'"file" if limit >= timeout_file_s else "budget"', r'"file"'),
            (CI, r"    deadline = started + effective - setup_elapsed_s", r"    deadline = started + effective"),
            (CI, r"    effective = first_run_budget_s if first_run else budget_s", r"    effective = budget_s"),
            (CI, r'    if build_cache == "miss" or inspector_cached is False:', r'    if build_cache == "miss":'),
            (CI, r'    if build_cache == "partial":', r"    if False:"),
            (CI, r'"cache_cold_extension": first_run and not infra and elapsed > budget_s,',
             r'"cache_cold_extension": first_run and elapsed > budget_s,'),
            (CI, r"        if a.started_at:", r"        if False:"),
        ],
    },
    # camada 2, instrução 15: gerador de target_trusted_roots (D-53, D-54)
    "gen_tcb_roots": {
        "tests": ["tests/maintenance/test_layer2_tools.py"],
        "mutations": [
            (GT, r'"lake_manifest_sha256": hashlib.sha256(normalize_newlines(mf_bytes)).hexdigest(),',
             r'"lake_manifest_sha256": hashlib.sha256(mf_bytes).hexdigest(),'),
            (GT, r'    if git("merge-base", "--is-ancestor", pinned, "HEAD").returncode != 0:', r"    if False:"),
            (GT, r'    d = git("diff", "--name-only", pinned)', r'    d = git("diff", "--name-only", pinned, "HEAD")'),
            (GT, r'    outside = [f for f in changed if not f.startswith(FORK_PREFIXES)]', r"    outside = []"),
            # instrução 18 (D-59): voltar a rejeitar `.auditor/`
            (GT, r'FORK_PREFIXES = (".github/", ".auditor/")', r'FORK_PREFIXES = (".github/",)'),
            (GT, r'    lean = [f for f in changed if f.endswith(".lean")]', r"    lean = []"),
            (GT, r'            data["derived_from"]["commit"] = pinned', r"            pass"),
            (GT, r"            if head != revs[name]:", r"            if False:"),
            (GT, r"    if missing:", r"    if False:"),
        ],
    },
}
