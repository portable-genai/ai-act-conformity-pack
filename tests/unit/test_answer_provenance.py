"""The service half of the model pills: which model ANSWERED, and whether it searched.

The console shows two pills at the top right: the model that answered the last request, and
``Search`` when that answer used an online search tool. Both come from response headers the kit
emits (``install_answer_provenance`` in ``api/app.py``) for whatever the model adapters NOTED as
they called. Before a request is answered the pill shows ``generator_model`` from ``/healthz``,
so that value must be the model the bound adapter calls, never one a configuration flag names
while the adapter calls another.

The managed narrator and retrieval adapters are driven here through a FAKE ``google.genai``
module. Neither attaches an online search tool, so neither notes a search. Neither sends a
temperature: narration is drafting, and free sampling means the parameter is absent.
"""

from __future__ import annotations

import dataclasses
import sys
import types
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from hex_service_kit import provenance

from conformity_pack import config
from conformity_pack.adapters.gcp.narrator import CloudNarratorAdapter
from conformity_pack.adapters.gcp.retrieval import CloudRetrievalAdapter
from conformity_pack.adapters.local.narrator import LocalNarratorAdapter
from conformity_pack.config import Settings

from tests import REPO_ROOT
from tests.conftest import local_settings
from tests.fixtures import sample_cases

ANSWERED_BY = "x-answered-by"
SEARCH_USED = "x-search-used"
STUB = LocalNarratorAdapter.MODEL
_AUDITOR = {"X-Dev-Persona": "auditor"}


def _assess(api_client: TestClient) -> dict[str, str]:
    response = api_client.post(
        "/v1/assess", json={"system": sample_cases.ESCALATING_SYSTEM}, headers=_AUDITOR
    )
    assert response.status_code == 200, response.text
    return dict(response.headers)


def test_the_local_narrator_answers_as_the_stub_the_pill_first_names(
    api_client: TestClient,
) -> None:
    """Under ``local`` the pill before and after the answer name the same stub."""
    headers = _assess(api_client)
    assert headers[ANSWERED_BY] == STUB == local_settings().generator_model
    assert SEARCH_USED not in headers


def test_a_call_that_searched_says_so_and_the_next_request_starts_fresh(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = LocalNarratorAdapter.narrate

    def searching(self: LocalNarratorAdapter, prompt: str) -> str:
        provenance.note_model("fake-searching-model")
        provenance.note_search()
        return original(self, prompt)

    monkeypatch.setattr(LocalNarratorAdapter, "narrate", searching)
    headers = _assess(api_client)
    assert headers[ANSWERED_BY] == f"fake-searching-model, {STUB}"
    assert headers[SEARCH_USED] == "true"
    monkeypatch.setattr(LocalNarratorAdapter, "narrate", original)
    headers = _assess(api_client)
    assert headers[ANSWERED_BY] == STUB
    assert SEARCH_USED not in headers


# --------------------------------------------------------------------------------------- #
# The Gemini adapters, through a fake SDK.
# --------------------------------------------------------------------------------------- #
def _fake_genai(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def generate_content(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return SimpleNamespace(text='{"narrative": "ok"}')

    genai = types.ModuleType("google.genai")
    genai.Client = lambda **_: SimpleNamespace(  # type: ignore[attr-defined]
        models=SimpleNamespace(generate_content=generate_content)
    )
    google = sys.modules.get("google") or types.ModuleType("google")
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setattr(google, "genai", genai, raising=False)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    return calls


def _gcp_settings() -> Settings:
    return dataclasses.replace(local_settings(), profile="gcp")


def test_the_gemini_narrator_notes_the_model_the_pill_first_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_genai(monkeypatch)
    with provenance.scope() as record:
        CloudNarratorAdapter(_gcp_settings()).narrate("FACTS:\n{}")
    assert record.models == [calls[0]["model"]] == [_gcp_settings().generator_model]
    assert record.search_used is False
    assert "config" not in calls[0], "narration is drafting: no temperature is sent"


def test_the_gemini_retrieval_notes_its_model_and_no_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _fake_genai(monkeypatch)
    with provenance.scope() as record:
        CloudRetrievalAdapter(_gcp_settings()).search("high-risk obligations")
    assert record.models == [calls[0]["model"]]
    assert record.search_used is False


# --------------------------------------------------------------------------------------- #
# generator_model is the model the adapter calls.
# --------------------------------------------------------------------------------------- #
def test_no_flag_swaps_in_a_model_the_adapter_never_calls() -> None:
    """The latent false banner: a flag that moved the pill but not the model that answered."""
    models = SimpleNamespace(
        reasoning="the-model-the-adapter-calls",
        hard_reasoning="a-model-nobody-calls",
        use_hard_reasoning=True,
    )
    named = config._model_from_settings(SimpleNamespace(models=models), "models.reasoning")
    assert named == "the-model-the-adapter-calls"


def test_the_hard_reasoning_flag_does_not_exist() -> None:
    settings_file = (REPO_ROOT / "config" / "settings.yaml").read_text(encoding="utf-8")
    assert "use_hard_reasoning" not in settings_file
    for source in sorted((REPO_ROOT / "src").rglob("*.py")):
        assert "use_hard_reasoning" not in source.read_text(encoding="utf-8"), source
