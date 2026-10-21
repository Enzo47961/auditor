"""Etapa A — pré-scan léxico do arquivo-alvo.

Contrato:
  * NUNCA emite conclusão positiva. `StageAResult` não tem campo de "ok"/"passou".
    Só produz: candidatos (`findings`), entradas não reconhecidas (`unrecognized`,
    que o agregador converte em fail-closed) e avisos (`warnings`).
  * É varredura léxica, não parsing (limitations.md, L-2). Comentários são
    ignorados para tokens, mas NÃO para a varredura de Unicode proibido.
  * Allow-list de comandos: selecionada pelo `lean-toolchain` do projeto-alvo.
    Sem allow-list para aquele toolchain → `allowlist_unavailable` (fail-closed).
"""
from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

STAGE_A_VERSION = "1"
DATA = Path(__file__).resolve().parent.parent / "data"
CONFUSABLES_FILE = DATA / "unicode" / "confusables-16.0.0.txt"

# Unicode proibido em qualquer posição (inclusive comentários e strings): Trojan Source.
BIDI_CONTROLS = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}
ZERO_WIDTH = {0x180E, 0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF}

NOT_IDENT_LETTERS = {"λ", "Π", "Σ"}  # letras gregas que o Lean reserva como símbolos
DECL_KEYWORDS = {"theorem", "lemma", "def", "abbrev", "instance", "example", "structure",
                 "class", "inductive", "coinductive", "opaque", "axiom"}
ANONYMOUS_OK = {"instance", "example"}


# --------------------------------------------------------------------------- tipos

@dataclass(frozen=True)
class Token:
    kind: str          # ident | symbol | number | string | char | doc | hashcmd
    text: str
    line: int          # 1-based
    col: int           # 0-based, em code points
    quoted: bool = False  # identificador com algum componente «…»


@dataclass(frozen=True)
class Item:
    code: str
    line: int
    col: int
    detail: dict = field(default_factory=dict)


@dataclass
class StageAResult:
    file: str
    toolchain: str | None
    allowlist: dict | None          # metadados da allow-list usada (versões)
    stage_a_version: str = STAGE_A_VERSION
    findings: list[Item] = field(default_factory=list)
    unrecognized: list[Item] = field(default_factory=list)
    warnings: list[Item] = field(default_factory=list)
    declarations: list[Item] = field(default_factory=list)


class LexError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(msg)
        self.line, self.col = line, col


# --------------------------------------------------------------------------- léxico

def _is_ident_start(c: str) -> bool:
    return c == "_" or (c.isalpha() and c not in NOT_IDENT_LETTERS)


def _is_ident_rest(c: str) -> bool:
    return (c.isalnum() or c in "_'!?" or unicodedata.category(c) in ("No", "Lm")) \
        and c not in NOT_IDENT_LETTERS


def lex(src: str) -> list[Token]:
    toks: list[Token] = []
    i, n, line, col = 0, len(src), 1, 0

    def adv(k: int = 1) -> None:
        nonlocal i, line, col
        for _ in range(k):
            if src[i] == "\n":
                line, col = line + 1, 0
            else:
                col += 1
            i += 1

    while i < n:
        c = src[i]
        sl, sc = line, col
        if c in " \t\r\n":
            adv(); continue
        if src.startswith("--", i):
            while i < n and src[i] != "\n":
                adv()
            continue
        if src.startswith("/-", i):
            is_doc = src.startswith("/--", i) or src.startswith("/-!", i)
            start = i
            depth = 0
            while True:
                if i >= n:
                    raise LexError("comentário de bloco não terminado", sl, sc)
                if src.startswith("/-", i):
                    depth += 1; adv(2); continue
                if src.startswith("-/", i):
                    depth -= 1; adv(2)
                    if depth == 0:
                        break
                    continue
                adv()
            if is_doc:
                toks.append(Token("doc", src[start:i], sl, sc))
            continue
        if c == '"':
            adv()
            while True:
                if i >= n:
                    raise LexError("string não terminada", sl, sc)
                if src[i] == "\\":
                    adv(2); continue
                if src[i] == '"':
                    adv(); break
                adv()
            toks.append(Token("string", "", sl, sc)); continue
        if c == "r" and i + 1 < n and src[i + 1] in '#"':
            j = i + 1
            while j < n and src[j] == "#":
                j += 1
            if j < n and src[j] == '"':
                hashes = j - i - 1
                close = '"' + "#" * hashes
                adv(j - i + 1)
                end = src.find(close, i)
                if end < 0:
                    raise LexError("raw string não terminada", sl, sc)
                adv(end - i + len(close))
                toks.append(Token("string", "", sl, sc)); continue
        if c == "'":
            # literal de caractere: 'a' ou '\n' / '\x41' / '\u{…}'
            j = i + 1
            if j < n and src[j] == "\\":
                k = src.find("'", j + 2)
                if 0 < k <= j + 12:
                    adv(k - i + 1); toks.append(Token("char", "", sl, sc)); continue
            elif j + 1 < n and src[j + 1] == "'":
                adv(3); toks.append(Token("char", "", sl, sc)); continue
            adv(); toks.append(Token("symbol", "'", sl, sc)); continue
        if c == "#" and i + 1 < n and _is_ident_start(src[i + 1]):
            j = i + 1
            while j < n and _is_ident_rest(src[j]):
                j += 1
            text = src[i:j]
            adv(j - i); toks.append(Token("hashcmd", text, sl, sc)); continue
        if _is_ident_start(c) or c == "«":
            j, quoted, parts = i, False, []
            while True:
                if j < n and src[j] == "«":
                    k = src.find("»", j + 1)
                    if k < 0:
                        raise LexError("identificador «…» não terminado", sl, sc)
                    parts.append(src[j:k + 1]); quoted = True; j = k + 1
                elif j < n and _is_ident_start(src[j]):
                    k = j + 1
                    while k < n and _is_ident_rest(src[k]):
                        k += 1
                    parts.append(src[j:k]); j = k
                else:
                    break
                if j + 1 < n and src[j] == "." and (_is_ident_start(src[j + 1]) or src[j + 1] == "«"):
                    j += 1; continue
                break
            adv(j - i)
            toks.append(Token("ident", ".".join(parts), sl, sc, quoted)); continue
        if c.isdigit():
            j = i
            while j < n and (src[j].isalnum() or src[j] in "._"):
                j += 1
            text = src[i:j]
            adv(j - i); toks.append(Token("number", text, sl, sc)); continue
        for sym in ("@[", ":=", "=>", "|>.", "<|", "|>"):
            if src.startswith(sym, i):
                adv(len(sym)); toks.append(Token("symbol", sym, sl, sc)); break
        else:
            adv(); toks.append(Token("symbol", c, sl, sc))
    return toks


# --------------------------------------------------------------------------- unicode

def scan_forbidden_unicode(src: str) -> list[Item]:
    out, line, col = [], 1, 0
    for ch in src:
        cp = ord(ch)
        if cp in BIDI_CONTROLS or cp in ZERO_WIDTH:
            out.append(Item("forbidden_unicode", line, col, {
                "codepoint": f"U+{cp:04X}",
                "name": unicodedata.name(ch, "?"),
                "class": "bidi" if cp in BIDI_CONTROLS else "zero_width",
            }))
        if ch == "\n":
            line, col = line + 1, 0
        else:
            col += 1
    return out


@lru_cache(maxsize=1)
def _confusables() -> dict[str, str]:
    table = {}
    for raw in CONFUSABLES_FILE.read_text(encoding="utf-8-sig").splitlines():
        body = raw.split("#", 1)[0].strip()
        if not body:
            continue
        src, dst, *_ = (x.strip() for x in body.split(";"))
        table[chr(int(src, 16))] = "".join(chr(int(c, 16)) for c in dst.split())
    return table


def skeleton(s: str) -> str:
    """Esqueleto TR39 §4: NFD → mapeamento de confusables → NFD."""
    t = _confusables()
    return unicodedata.normalize("NFD", "".join(t.get(c, c) for c in unicodedata.normalize("NFD", s)))


def _components(tok: Token) -> list[str]:
    out, buf, depth = [], "", 0
    for ch in tok.text:
        if ch == "«":
            depth += 1
        elif ch == "»":
            depth -= 1
        if ch == "." and depth == 0:
            out.append(buf); buf = ""
        else:
            buf += ch
    out.append(buf)
    return out


def scan_confusables(tokens: list[Token]) -> list[Item]:
    """Avisos (nunca falha): pares de identificadores do arquivo com o mesmo
    esqueleto e grafias diferentes; e componentes «…» não-ASCII de esqueleto ASCII.
    Componentes de um caractere são ignorados (convenção matemática a/α)."""
    warnings: list[Item] = []
    groups: dict[str, dict[str, Token]] = {}
    for tok in (t for t in tokens if t.kind == "ident"):
        for comp in _components(tok):
            bare = comp.strip("«»")
            if comp.startswith("«") and not bare.isascii() and skeleton(bare).isascii():
                warnings.append(Item("confusable_quoted_identifier", tok.line, tok.col,
                                     {"identifier": comp, "skeleton": skeleton(bare)}))
            if len(bare) >= 2:
                groups.setdefault(skeleton(bare), {}).setdefault(bare, tok)
    for skel, spellings in groups.items():
        if len(spellings) >= 2:
            first = min(spellings.values(), key=lambda t: (t.line, t.col))
            warnings.append(Item("confusable_identifiers", first.line, first.col,
                                 {"skeleton": skel, "spellings": sorted(spellings)}))
    return warnings


# --------------------------------------------------------------------------- ambiente

def find_toolchain(target: Path) -> tuple[Path | None, str | None]:
    for d in [target.parent, *target.parent.parents]:
        f = d / "lean-toolchain"
        if f.is_file():
            return d, f.read_text(encoding="utf-8").strip()
    return None, None


def allowlist_path(toolchain: str) -> Path:
    return DATA / "allowlist" / (toolchain.replace("/", "__").replace(":", "__") + ".json")


def _norm(tokentext: str) -> str:
    return tokentext[1:-1] if tokentext.startswith("«") and tokentext.endswith("»") else tokentext


SET_KEYS = ("allowed", "syntax_extension", "metaprogramming", "continuation", "unclassified")


def _prepare(data: dict) -> dict:
    for k in SET_KEYS:
        data[k] = {_norm(x) for x in data.get(k, [])}
    return data


def load_allowlist(toolchain: str) -> dict | None:
    """Allow-list do core para o toolchain (empacotada)."""
    p = allowlist_path(toolchain)
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("toolchain") != toolchain:
        return None
    return _prepare(data)


def load_project_allowlist(path: Path, root: Path, toolchain: str) -> tuple[dict | None, str | None]:
    """Allow-list de projeto. Só é usada se corresponder ao pino ATUAL do ambiente
    (lean-toolchain + lake-manifest.json). Divergência → fail-closed (`allowlist_stale`).
    Não verifica correção semântica da classificação (L-16)."""
    from auditor.allowlist import env_pin   # import local: evita custo na importação
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return None, f"allow-list ilegível: {e}"
    manifest = root / "lake-manifest.json"
    if not manifest.is_file():
        return None, "lake-manifest.json ausente: pino do ambiente indeterminado"
    if data.get("kind") != "project":
        return None, "arquivo não é allow-list de projeto"
    if data.get("toolchain") != toolchain:
        return None, f"toolchain da allow-list {data.get('toolchain')!r} ≠ {toolchain!r}"
    if data.get("env_pin") != env_pin(toolchain, manifest.read_bytes()):
        return None, "pino do ambiente divergente (lake-manifest.json mudou)"
    return _prepare(data), None


# --------------------------------------------------------------------------- análise

PROJECT_ALLOWLIST_REL = Path(".auditor") / "allowlist.json"


def analyze(target: Path, src: str | None = None, allowlist_file: Path | None = None) -> StageAResult:
    """`allowlist_file`: allow-list de projeto explícita. Sem ela, usa
    `<raiz>/.auditor/allowlist.json` se existir; senão, a do core para o toolchain."""
    target = Path(target)
    root, toolchain = find_toolchain(target)
    res = StageAResult(file=str(target), toolchain=toolchain, allowlist=None)

    if src is None:
        try:
            src = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            res.unrecognized.append(Item("unreadable_input", 0, 0, {"error": str(e)}))
            return res

    res.unrecognized += scan_forbidden_unicode(src)

    allow = None
    if toolchain is None:
        res.unrecognized.append(Item("environment_unpinned", 0, 0,
                                     {"detail": "lean-toolchain não encontrado"}))
    else:
        proj_file = allowlist_file or (root / PROJECT_ALLOWLIST_REL)
        if allowlist_file is not None or proj_file.is_file():
            allow, why = load_project_allowlist(proj_file, root, toolchain)
            if allow is None:
                res.unrecognized.append(Item("allowlist_stale", 0, 0, {"file": str(proj_file), "detail": why}))
        else:
            allow = load_allowlist(toolchain)
            if allow is None:
                res.unrecognized.append(Item("allowlist_unavailable", 0, 0, {"toolchain": toolchain}))
        if allow is not None:
            res.allowlist = {k: allow.get(k) for k in (
                "kind", "toolchain", "env_pin", "generator_version", "classification_version",
                "project_classification_sha256")}

    try:
        toks = lex(src)
    except LexError as e:
        res.unrecognized.append(Item("lex_error", e.line, e.col, {"error": str(e)}))
        return res

    res.warnings += scan_confusables(toks)
    _scan_tokens(toks, allow, res)
    return res


def _scan_tokens(toks: list[Token], allow: dict | None, res: StageAResult) -> None:
    risky_syntax = allow["syntax_extension"] if allow else set()
    risky_meta = allow["metaprogramming"] if allow else set()
    unclassified = allow["unclassified"] if allow else set()
    ns: list[str | None] = []

    def nxt(k: int, off: int = 1) -> Token | None:
        return toks[k + off] if k + off < len(toks) else None

    prev_line = 0
    for k, t in enumerate(toks):
        first_on_line = t.line != prev_line
        prev_line = t.line

        # --- comandos na coluna 0 contra a allow-list
        if allow is not None and first_on_line and t.col == 0:
            key = t.text if t.kind in ("ident", "symbol", "hashcmd") else (
                t.text[:3] if t.kind == "doc" else None)
            if key is not None and key not in allow["allowed"] and key not in allow["continuation"] \
                    and key not in risky_syntax and key not in risky_meta and key not in unclassified:
                res.unrecognized.append(Item("unknown_command", t.line, t.col, {"token": key}))

        # --- comandos de risco em qualquer posição (são tokens reservados)
        word = t.text
        if t.kind == "ident" and (n1 := nxt(k)) is not None and n1.text == "%" \
                and (word + "%") in (risky_syntax | risky_meta):
            word = word + "%"
        if t.kind in ("ident", "hashcmd", "symbol") and not t.quoted:
            if word in risky_syntax:
                res.unrecognized.append(Item("syntax_extension_declared", t.line, t.col, {"command": word}))
            elif word in risky_meta:
                res.unrecognized.append(Item("metaprogramming_command", t.line, t.col, {"command": word}))
            elif word in unclassified:
                res.unrecognized.append(Item("unclassified_command", t.line, t.col, {"command": word}))

        if t.kind != "ident" or t.quoted:
            continue

        # --- escopos (para nomes qualificados)
        if t.text == "namespace" and (n1 := nxt(k)) and n1.kind == "ident":
            ns.extend(n1.text.split("."))
        elif t.text == "section":
            ns.append(None)
        elif t.text == "end":
            n1 = nxt(k)
            count = len(n1.text.split(".")) if (n1 and n1.kind == "ident" and n1.line == t.line) else 1
            for _ in range(count):
                if ns:
                    ns.pop()

        # --- candidatos
        if t.text in ("sorry", "admit"):
            res.findings.append(Item(t.text, t.line, t.col))
        elif t.text == "native_decide":
            res.findings.append(Item("native_decide", t.line, t.col, {"form": "native_decide"}))
        elif t.text == "native":
            p, n1 = (toks[k - 1] if k else None), nxt(k)
            if p is not None and p.text == "+":
                res.findings.append(Item("native_decide", t.line, t.col, {"form": "+native"}))
            elif n1 is not None and n1.text == ":=":
                res.findings.append(Item("native_decide", t.line, t.col, {"form": "native := …"}))
        elif t.text == "implemented_by":
            n1 = nxt(k)
            res.findings.append(Item("implemented_by", t.line, t.col,
                                     {"implementation": n1.text if n1 and n1.kind == "ident" else None}))
        elif t.text == "unlock_limits":
            # `unlock_limits` zera os limites de recurso (doc do comando em v4.36.0-rc1): é
            # registrado como os `set_option … 0` equivalentes, para a política decidir (D-41).
            n1 = nxt(k)
            scoped = n1 is not None and n1.kind == "ident" and n1.text == "in"
            for opt in UNLOCK_LIMITS_OPTIONS:
                res.findings.append(Item("set_option", t.line, t.col, {
                    "option": opt, "value": "0", "via": "unlock_limits",
                    "scope": "in" if scoped else "file_or_section",
                    "applies_to": _bound_declaration(toks, k + 2, ns) if scoped else None,
                }))
        elif t.text == "set_option":
            n1, n2, n3 = nxt(k), nxt(k, 2), nxt(k, 3)
            scoped = n3 is not None and n3.kind == "ident" and n3.text == "in"
            res.findings.append(Item("set_option", t.line, t.col, {
                "option": n1.text if n1 and n1.kind == "ident" else None,
                "value": n2.text if n2 is not None else None,
                "scope": "in" if scoped else "file_or_section",
                "applies_to": _bound_declaration(toks, k + 4, ns) if scoped else None,
            }))

        # --- declarações
        if t.text in DECL_KEYWORDS:
            n1 = nxt(k)
            name = None
            if n1 is not None and n1.kind == "ident" and t.text not in ("example",) \
                    and not (t.text == "instance" and n1.text in ("priority",)):
                raw = n1.text
                name = raw[len("_root_."):] if raw.startswith("_root_.") else \
                    ".".join([*(x for x in ns if x), raw])
            if name is None and t.text not in ANONYMOUS_OK:
                res.unrecognized.append(Item("declaration_name_unresolved", t.line, t.col, {"keyword": t.text}))
            res.declarations.append(Item("declaration", t.line, t.col, {"keyword": t.text, "name": name}))
            if t.text == "axiom":
                res.findings.append(Item("axiom", t.line, t.col, {"name": name}))


UNLOCK_LIMITS_OPTIONS = ("maxRecDepth", "maxHeartbeats", "synthInstance.maxHeartbeats")

MODIFIERS = {"private", "protected", "noncomputable", "partial", "unsafe", "nonrec", "public", "meta"}


def _bound_declaration(toks: list[Token], k: int, ns: list[str | None]) -> str | None:
    """Declaração à qual `set_option … in` se vincula: o COMANDO imediatamente seguinte.

    Pula docstrings, blocos `@[…]`, modificadores e outros `set_option … in` encadeados.
    Se o comando seguinte não for uma declaração com nome, retorna None (sem vínculo)."""
    while k < len(toks):
        t = toks[k]
        if t.kind == "doc" or (t.kind == "ident" and t.text in MODIFIERS):
            k += 1
        elif t.kind == "symbol" and t.text == "@[":
            depth = 1
            k += 1
            while k < len(toks) and depth:
                depth += toks[k].text in ("[", "@[")
                depth -= toks[k].text == "]"
                k += 1
        elif t.kind == "ident" and t.text == "set_option" and k + 3 < len(toks) \
                and toks[k + 3].text == "in":
            k += 4
        elif t.kind == "ident" and t.text == "unlock_limits" and k + 1 < len(toks) \
                and toks[k + 1].text == "in":
            k += 2
        elif t.kind == "ident" and t.text in DECL_KEYWORDS and t.text not in ANONYMOUS_OK \
                and k + 1 < len(toks) and toks[k + 1].kind == "ident":
            raw = toks[k + 1].text
            return raw[len("_root_."):] if raw.startswith("_root_.") else ".".join([*(x for x in ns if x), raw])
        else:
            return None
    return None
