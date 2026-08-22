"""Shared fixtures for every suite: the REAL local adapters, never bespoke fakes.

The offline implementation must live in exactly one place, so the unit suite drives
``adapters/local`` rather than a parallel set of in-memory doubles that can drift from it. Every
adapter constructs from a single ``Settings`` pointed at ``:memory:``, which is also the adapter
convention the contract suite asserts.

``no_cloud_sdk`` is the portability harness: it makes ``google`` and every submodule
UNIMPORTABLE for the duration of a test, so "the SDK-free profiles construct with no cloud SDK"
is proved by blocking the import rather than by hoping the machine has none installed.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator, Sequence
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient

from conformity_pack.config import (
    Container,
    Settings,
    build_container,
)
from conformity_pack.domain.conformity_service import (
    ConformityService,
)

from .fixtures import sample_cases


def build_conformity_service(container: Container) -> ConformityService:
    """The conformity service wired from a container's bound ports (the one construction site)."""
    return ConformityService(
        audit=container.audit,
        registry=container.registry,
        obligations=container.obligations,
        evidence=container.evidence,
        retrieval=container.retrieval,
        narrator=container.narrator,
        tracer=container.tracer,
        matrix_store=container.matrix_store,
    )


#: A loopback peer: the app-object exposure guard refuses the unauthenticated local posture to
#: any other peer, and TestClient's default peer is the literal host "testclient".
LOOPBACK_PEER = ("127.0.0.1", 50000)

#: The prefix whose imports the SDK-free proof blocks (every managed SDK this repo lazily uses).
BLOCKED_SDK_ROOTS: tuple[str, ...] = ("google",)


def local_settings(**overrides: Any) -> Settings:
    """``local`` profile settings on ephemeral stores, plus any per-test override."""
    base: dict[str, Any] = {
        "profile": "local",
        "audit_path": ":memory:",
        "tenant": sample_cases.TENANT,
    }
    base.update(overrides)
    return Settings(**base)


def is_blocked_sdk(fullname: str, roots: Sequence[str] = BLOCKED_SDK_ROOTS) -> bool:
    """True when ``fullname`` is one of the blocked roots or lives under one."""
    return any(fullname == root or fullname.startswith(root + ".") for root in roots)


class _BlockedSdkFinder:
    """A meta-path finder that refuses the blocked roots, whatever is installed."""

    def find_spec(self, fullname: str, path: object = None, target: object = None) -> None:
        if is_blocked_sdk(fullname):
            raise ModuleNotFoundError(
                f"{fullname} is blocked: this profile must construct with no cloud SDK present"
            )
        return None


@pytest.fixture()
def settings() -> Settings:
    return local_settings()


@pytest.fixture()
def container(settings: Settings) -> Container:
    return build_container(settings)


@pytest.fixture()
def conformity_service(container: Container) -> ConformityService:
    return build_conformity_service(container)


@pytest.fixture()
def api_client() -> Iterator[TestClient]:
    """The API served to a loopback peer, which is the only posture the local profile allows.

    The module is RE-IMPORTED rather than imported, because the API's whole posture is decided at
    import and ``tests/unit/test_iap_identity.py`` deliberately re-imports it under the managed
    profile to prove the IAP refusals. That leaves a managed app in ``sys.modules``, so a plain
    import here would hand a later test whichever app happened to be built last and answer its
    seeded-persona requests with 401. Rebuilding under the ambient environment makes this fixture
    mean what its name says regardless of collection order, rather than making every API test
    depend on sorting before the letter i.
    """
    app = reimport("conformity_pack.api.app").app

    with TestClient(app, client=LOOPBACK_PEER) as client:
        yield client


@pytest.fixture()
def no_cloud_sdk() -> Iterator[None]:
    """Make the managed SDKs unimportable, and restore the interpreter afterwards."""
    finder = _BlockedSdkFinder()
    evicted: dict[str, ModuleType] = {
        name: module for name, module in sys.modules.items() if is_blocked_sdk(name)
    }
    for name in evicted:
        del sys.modules[name]
    sys.meta_path.insert(0, finder)  # type: ignore[arg-type]
    try:
        yield
    finally:
        sys.meta_path.remove(finder)  # type: ignore[arg-type]
        sys.modules.update(evicted)


def reimport(module_name: str) -> ModuleType:
    """Import ``module_name`` from scratch, so an import-time failure is actually observed."""
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)
