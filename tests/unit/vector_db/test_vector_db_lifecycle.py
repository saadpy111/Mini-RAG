import asyncio
from types import SimpleNamespace

import pytest
from fastapi import FastAPI

from src.helpers.result_pattern import Result
from src.vector_db import VectorDBLifecycle
from src.vector_db.VectorDBModels import VectorCollectionConfig


class FakeProvider:
    def __init__(self, initialize_result=None, collections_result=None):
        self.initialize_result = initialize_result or Result.success(None)
        self.collections_result = collections_result or Result.success(None)
        self.initialize_called = False
        self.ensure_collections_called = False
        self.close_called = False

    async def initialize(self):
        self.initialize_called = True
        return self.initialize_result

    async def ensure_collections(self):
        self.ensure_collections_called = True
        return self.collections_result

    async def close(self):
        self.close_called = True


def configure_lifecycle(monkeypatch, provider, provider_name="fake"):
    monkeypatch.setattr(
        VectorDBLifecycle,
        "settings",
        SimpleNamespace(
            vector_db_provider=provider_name,
            vector_db_collections=[
                VectorCollectionConfig(name="chunks", dimension=1024)
            ],
        ),
    )
    monkeypatch.setattr(
        VectorDBLifecycle,
        "VECTOR_DB_PROVIDER_BUILDERS",
        {"fake": lambda collections: provider},
    )


def test_lifespan_initializes_collections_and_closes_provider(monkeypatch):
    provider = FakeProvider()
    configure_lifecycle(monkeypatch, provider)
    app = FastAPI()

    async def exercise():
        async with VectorDBLifecycle.vector_db_lifespan(app):
            assert app.state.vector_db_provider is provider

    asyncio.run(exercise())

    assert provider.initialize_called is True
    assert provider.ensure_collections_called is True
    assert provider.close_called is True


def test_lifespan_closes_provider_when_connection_fails(monkeypatch):
    provider = FakeProvider(
        initialize_result=Result.failure("connection failed")
    )
    configure_lifecycle(monkeypatch, provider)
    app = FastAPI()

    async def exercise():
        async with VectorDBLifecycle.vector_db_lifespan(app):
            pytest.fail("Lifespan should not yield after a connection failure")

    with pytest.raises(RuntimeError, match="connection failed"):
        asyncio.run(exercise())

    assert provider.ensure_collections_called is False
    assert provider.close_called is True
    assert not hasattr(app.state, "vector_db_provider")


def test_lifespan_closes_provider_when_collection_setup_fails(monkeypatch):
    provider = FakeProvider(
        collections_result=Result.failure("collection setup failed")
    )
    configure_lifecycle(monkeypatch, provider)
    app = FastAPI()

    async def exercise():
        async with VectorDBLifecycle.vector_db_lifespan(app):
            pytest.fail("Lifespan should not yield after a collection failure")

    with pytest.raises(RuntimeError, match="collection setup failed"):
        asyncio.run(exercise())

    assert provider.initialize_called is True
    assert provider.close_called is True
    assert not hasattr(app.state, "vector_db_provider")


def test_lifespan_rejects_unknown_provider_before_startup(monkeypatch):
    configure_lifecycle(
        monkeypatch,
        provider=FakeProvider(),
        provider_name="missing",
    )
    app = FastAPI()

    async def exercise():
        async with VectorDBLifecycle.vector_db_lifespan(app):
            pytest.fail("Lifespan should not yield for an unknown provider")

    with pytest.raises(RuntimeError):
        asyncio.run(exercise())


def test_lifespan_closes_provider_when_application_body_raises(monkeypatch):
    provider = FakeProvider()
    configure_lifecycle(monkeypatch, provider)
    app = FastAPI()

    async def exercise():
        async with VectorDBLifecycle.vector_db_lifespan(app):
            raise ValueError("body failed")

    with pytest.raises(ValueError, match="body failed"):
        asyncio.run(exercise())

    assert provider.close_called is True
