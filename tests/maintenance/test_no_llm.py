"""DoD: nenhuma dependência de LLM no código (princípio 4).

Verificação mecânica, inclusive TRANSITIVA: o fecho das dependências Python instaladas do
auditor (o mesmo registrado na TCB, D-20) não pode conter biblioteca de LLM; nenhum import
nem endpoint de API de LLM no código-fonte Python ou Lean."""
import re

import pytest

from auditor import pydeps
from conftest import ROOT

LLM_PACKAGES = {"anthropic", "openai", "langchain", "langchain-core", "langchain-openai",
                "langchain-community", "transformers", "google-generativeai", "google-genai",
                "mistralai", "cohere", "ollama", "llama-cpp-python", "litellm", "vllm",
                "huggingface-hub", "together", "groq", "sentence-transformers", "tiktoken",
                "llama-index", "instructor", "dspy", "guidance"}
LLM_MODULES = {"anthropic", "openai", "langchain", "langchain_core", "langchain_openai", "transformers",
               "google.generativeai", "google.genai", "mistralai", "cohere", "ollama", "llama_cpp",
               "litellm", "vllm", "huggingface_hub", "together", "groq", "tiktoken", "llama_index"}
LLM_ENDPOINTS = re.compile(r"api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com"
                           r"|api\.mistral\.ai|api\.cohere\.|api\.together\.|api\.groq\.com|bedrock-runtime")
IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.M)
SOURCES = [*(ROOT / "src").rglob("*.py"), *(ROOT / "tools").rglob("*.py")]
LLM_NORMALIZED = {pydeps.normalize(p) for p in LLM_PACKAGES}


def llm_in(deps) -> set:
    return {d for d in deps if pydeps.normalize(d) in LLM_NORMALIZED}


def test_no_llm_in_transitive_closure_of_installed_dependencies():
    deps = pydeps.closure(pydeps.declared())
    assert "jsonschema" in deps                  # o fecho foi de fato percorrido
    assert llm_in(deps) == set(), deps


def test_detector_catches_transitive_llm_dependency():
    """Um pacote inofensivo que puxa, dois níveis abaixo, uma biblioteca de LLM é pego."""
    graph = {"jsonschema": ["helper>=1"], "helper": ["deep ; python_version >= '3'"],
             "deep": ["openai>=1"], "openai": []}
    deps = pydeps.closure(["jsonschema"], requires=lambda n: graph.get(n),
                          version=lambda n: "1.0" if n in graph else None)
    assert llm_in(deps) == {"openai"}


def test_missing_declared_dependency_fails_closed():
    with pytest.raises(pydeps.DependencyError):
        pydeps.closure(["ghost-package"], requires=lambda n: [], version=lambda n: None)


def test_no_llm_imports_in_sources():
    assert SOURCES
    for f in SOURCES:
        for m in IMPORT.finditer(f.read_text(encoding="utf-8")):
            mod = m.group(1) or m.group(2)
            assert not any(mod == p or mod.startswith(p + ".") for p in LLM_MODULES), (f, mod)


def test_no_llm_endpoints_anywhere():
    for f in [*SOURCES, *(ROOT / "src").rglob("*.lean"), ROOT / "policy.toml"]:
        assert not LLM_ENDPOINTS.search(f.read_text(encoding="utf-8")), f
