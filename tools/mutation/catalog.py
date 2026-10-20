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
            (TB, r'        if module.split(".")[0] not in b.toolchain_roots:', r"        if False:"),
            (TB, r"        if _norm(p) != _norm(b.toolchain_lib / rel):", r"        if False:"),
            (FP, r"        if not isinstance(v, dict) or any(not v.get(k) for k in keys):",
             r"        if not isinstance(v, dict):"),
            (PD, "            if has_marker:\n                continue\n            raise DependencyError",
             "            if True:\n                continue\n            raise DependencyError"),
            (PD, r'            if "extra" in marker:', r"            if True:"),
        ],
    },
    "ci": {
        "tests": ["tests/ci"],
        "mutations": [
            (CI, r"        if remaining < MIN_SLICE_S:", r"        if False:"),
            (CI, r'    infra = [r for r in results if r["status"] in ("infra", "skipped_budget", "killed_timeout")]',
             r'    infra = [r for r in results if r["status"] in ("infra",)]'),
            (CI, r'        return 1 if outcome["audit_failed"] else 0', r'        return 1 if outcome["audit_failed"] or outcome["infra_failed"] else 0'),
            (CI, r'    if conclusion not in ("success", "failure"):', r"    if False:"),
            (CI, r'            or not isinstance(data.get("infra_failed"), bool):', r"            or False:"),
            (CI, '    if data["infra_failed"]:\n        return True, "infra_failed"', '    if False:\n        return True, "infra_failed"'),
            (CI, '        return True, "outcome ausente"', '        return False, "outcome ausente"'),
            (CI, r'            entry["status"] = {0: "pass", 1: "fail", 2: "infra"}.get(entry["exit_code"], "infra")',
             r'            entry["status"] = {0: "pass", 1: "fail", 2: "pass"}.get(entry["exit_code"], "pass")'),
        ],
    },
}
