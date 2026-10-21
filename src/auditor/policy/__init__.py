"""Policy engine: carregamento estrito do `policy.toml` e gramática da justificativa.

Lacuna A: política ausente, ilegível, com chave desconhecida, tipo errado ou valor fora do
domínio → `PolicyError`. O chamador NÃO aplica default: todas as declarações saem
`Não resolvida` / `Não resolvido`, razão `policy_invalid`, exit 2.

As regras em si (o que cada fato significa) estão em `auditor.aggregator`; aqui só se
valida e se expõe a política como dados.
"""
from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class Policy:
    version: str
    sha256: str
    allowed_axioms: frozenset[str]
    admissions: frozenset[str]
    forbidden_axioms: frozenset[str]
    native_evaluation: frozenset[str]
    unknown_axiom_action: str
    unknown_axiom_justification: str
    native_attributes: tuple[str, ...]
    trusted_boundary: str
    forbidden_options: tuple[tuple[str, str], ...]
    allowed_options: tuple[str, ...]
    exemption_paths: tuple[str, ...]
    exemption_reason: str
    native_auxiliary_action: str = "fail_closed"

    def option_recognized(self, option: str) -> bool:
        return any(option == a or (a.endswith(".") and option.startswith(a)) for a in self.allowed_options)


SCHEMA = {
    "": {"policy_version": str, "axioms": dict, "native_implementations": dict, "set_option": dict},
    "axioms": {"allowed": list, "admissions": list, "forbidden": list, "native_evaluation": list,
               "native_auxiliary_action": str,
               "unknown_axiom_action": str, "unknown_axiom_justification": str},
    "native_implementations": {"attributes": list, "trusted_boundary": str},
    "set_option": {"forbidden": list, "allowed": list, "heartbeat_exemption": dict},
    "set_option.heartbeat_exemption": {"paths": list, "reason": str},
}
UNKNOWN_AXIOM_ACTIONS = ("fail_closed", "allow_with_warning")
NATIVE_AUXILIARY_ACTIONS = ("fail_closed",)    # única opção na Fase 0 (Q9-a, instrução 13)
KNOWN_ATTRIBUTES = ("implemented_by", "extern")
KNOWN_BOUNDARIES = ("toolchain",)


def _check_table(path: str, table: dict) -> None:
    spec = SCHEMA[path]
    missing = set(spec) - set(table)
    extra = set(table) - set(spec)
    if missing:
        raise PolicyError(f"[{path or 'raiz'}] chaves obrigatórias ausentes: {sorted(missing)}")
    if extra:
        raise PolicyError(f"[{path or 'raiz'}] chaves desconhecidas: {sorted(extra)}")
    for k, t in spec.items():
        if not isinstance(table[k], t):
            raise PolicyError(f"[{path or 'raiz'}] {k}: esperado {t.__name__}")


def _names(path: str, xs: list) -> frozenset[str]:
    if not all(isinstance(x, str) and x for x in xs):
        raise PolicyError(f"{path}: lista deve conter só nomes não vazios")
    if len(set(xs)) != len(xs):
        raise PolicyError(f"{path}: nomes duplicados")
    return frozenset(xs)


def load_policy(path: Path) -> Policy:
    try:
        raw = Path(path).read_bytes()
    except OSError as e:
        raise PolicyError(f"política ilegível: {e}") from e
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
        raise PolicyError(f"política malformada: {e}") from e

    _check_table("", data)
    ax, ni, so = data["axioms"], data["native_implementations"], data["set_option"]
    _check_table("axioms", ax)
    _check_table("native_implementations", ni)
    _check_table("set_option", so)
    _check_table("set_option.heartbeat_exemption", so["heartbeat_exemption"])

    lists = {k: _names(f"axioms.{k}", ax[k]) for k in ("allowed", "admissions", "forbidden", "native_evaluation")}
    seen: dict[str, str] = {}
    for k, names in lists.items():
        for n in names:
            if n in seen:
                raise PolicyError(f"axioma {n!r} em duas listas: {seen[n]} e {k}")
            seen[n] = k
    if ax["native_auxiliary_action"] not in NATIVE_AUXILIARY_ACTIONS:
        raise PolicyError(f"native_auxiliary_action desconhecida: {ax['native_auxiliary_action']!r} "
                          f"(conhecidas: {NATIVE_AUXILIARY_ACTIONS})")
    if ax["unknown_axiom_action"] not in UNKNOWN_AXIOM_ACTIONS:
        raise PolicyError(f"unknown_axiom_action desconhecida: {ax['unknown_axiom_action']!r}")
    if ax["unknown_axiom_action"] == "allow_with_warning" and not ax["unknown_axiom_justification"].strip():
        raise PolicyError("allow_with_warning exige unknown_axiom_justification não vazia")

    attrs = tuple(ni["attributes"])
    if not attrs or any(a not in KNOWN_ATTRIBUTES for a in attrs) or len(set(attrs)) != len(attrs):
        raise PolicyError(f"native_implementations.attributes inválido: {attrs!r} (conhecidos: {KNOWN_ATTRIBUTES})")
    if ni["trusted_boundary"] not in KNOWN_BOUNDARIES:
        raise PolicyError(f"trusted_boundary desconhecida: {ni['trusted_boundary']!r}")

    forbidden_opts = []
    for item in so["forbidden"]:
        if not isinstance(item, dict) or set(item) != {"option", "value"} \
                or not all(isinstance(v, str) and v for v in item.values()):
            raise PolicyError(f"set_option.forbidden: entrada inválida {item!r}")
        forbidden_opts.append((item["option"], item["value"]))
    allowed_opts = tuple(sorted(_names("set_option.allowed", so["allowed"])))
    ex = so["heartbeat_exemption"]
    paths = tuple(sorted(_names("set_option.heartbeat_exemption.paths", ex["paths"])))
    if not ex["reason"].strip():
        raise PolicyError("set_option.heartbeat_exemption.reason vazio")

    if not isinstance(data["policy_version"], str) or not data["policy_version"]:
        raise PolicyError("policy_version vazio")
    return Policy(
        version=data["policy_version"],
        sha256="sha256:" + hashlib.sha256(raw).hexdigest(),
        allowed_axioms=lists["allowed"], admissions=lists["admissions"],
        forbidden_axioms=lists["forbidden"], native_evaluation=lists["native_evaluation"],
        unknown_axiom_action=ax["unknown_axiom_action"],
        unknown_axiom_justification=ax["unknown_axiom_justification"],
        native_attributes=attrs, trusted_boundary=ni["trusted_boundary"],
        forbidden_options=tuple(forbidden_opts), allowed_options=allowed_opts,
        exemption_paths=paths, exemption_reason=ex["reason"],
        native_auxiliary_action=ax["native_auxiliary_action"],
    )


# --------------------------------------------------------------------------- justificativa

# Gramática estrita (O-1, opção B; limitations.md L-4): exatamente uma linha, sem escape,
# sem continuação. A única normalização é remover espaço em branco no FIM da linha.
JUSTIFICATION_PREFIX = "auditor_justified"
JUSTIFICATION_LINE = re.compile(r'auditor_justified: reason="([^"\\\r\n]+)" reviewer="@([A-Za-z0-9-]+)"')


@dataclass(frozen=True)
class Justification:
    status: str                  # "absent" | "valid" | "malformed"
    reason: str | None = None
    reviewer: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict | None:
        return {"reason": self.reason, "reviewer": self.reviewer} if self.status == "valid" else None


def parse_justification(docstring: str | None) -> Justification:
    if not docstring:
        return Justification("absent")
    lines = [ln for ln in docstring.splitlines() if ln.lstrip().startswith(JUSTIFICATION_PREFIX)]
    if not lines:
        return Justification("absent")
    if len(lines) > 1:
        return Justification("malformed", detail="mais de uma linha de justificativa")
    m = JUSTIFICATION_LINE.fullmatch(lines[0].rstrip())
    if m is None:
        return Justification("malformed", detail=f"linha fora da gramática: {lines[0].rstrip()!r}")
    return Justification("valid", reason=m.group(1), reviewer="@" + m.group(2))
