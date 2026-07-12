import sys
import types

import pytest

from crew import _build_llm


def test_build_llm_requires_any_supported_configuration(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    with pytest.raises(RuntimeError, match="No supported LLM API key"):
        _build_llm()


def test_build_llm_uses_gemini_when_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-gemini")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_crewai = types.ModuleType("crewai")
    fake_crewai.LLM = DummyLLM
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)

    llm = _build_llm()

    assert isinstance(llm, DummyLLM)
    assert captured["provider"] == "gemini"
    assert captured["model"] == "gemini-2.5-flash"


def test_build_llm_uses_openai_when_configured(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai")
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    fake_crewai = types.ModuleType("crewai")
    fake_crewai.LLM = DummyLLM
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)

    llm = _build_llm()

    assert isinstance(llm, DummyLLM)
    assert captured["provider"] == "openai"
    assert captured["model"] == "gpt-4o-mini"
