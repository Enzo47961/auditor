"""DoD: nenhuma dependência de LLM no código (princípio 4).

Verificação mecânica: nenhuma dependência declarada nem import, em código Python ou Lean,
de bibliotecas de LLM, e nenhum endpoint de API de LLM no código-fonte."""
import re
import tomllib

from conftest import ROOT

LLM_PACKAGES = {"anthropic", "openai", "langchain", "langchain_core", "langchain_openai", "transformers",
                "google.generativeai", "google.genai", "mistralai", "cohere", "ollama", "llama_cpp",
                "litellm", "vllm", "huggingface_hub", "together", "groq"}
LLM_ENDPOINTS = re.compile(r"api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com"
                           r"|api\.mistral\.ai|api\.cohere\.|api\.together\.|api\.groq\.com")
IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
SOURCES = [*(ROOT / "src").rglob("*.py"), *(ROOT / "tools").rglob("*.py")]


def test_no_llm_dependency_declared():
    proj = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    deps = list(proj.get("dependencies", []))
    for extra in proj.get("optional-dependencies", {}).values():
        deps += extra
    names = {re.split(r"[<>=!~\[ ]", d, maxsplit=1)[0].lower().replace("-", "_") for d in deps}
    assert not names & {p.replace(".", "_") for p in LLM_PACKAGES}, names


def test_no_llm_imports_in_sources():
    assert SOURCES
    for f in SOURCES:
        for m in IMPORT.finditer(f.read_text(encoding="utf-8")):
            mod = m.group(1) or m.group(2)
            assert not any(mod == p or mod.startswith(p + ".") for p in LLM_PACKAGES), (f, mod)


def test_no_llm_endpoints_anywhere():
    for f in [*SOURCES, *(ROOT / "src").rglob("*.lean"), ROOT / "policy.toml"]:
        assert not LLM_ENDPOINTS.search(f.read_text(encoding="utf-8")), f
