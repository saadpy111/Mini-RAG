from unittest.mock import Mock

from src.constants import ErrorCode
from src.helpers.result_pattern import ErrorType
from src.vector_db.VectorDBModels import VectorCollectionConfig
from src.vector_db.VectorDBProviderFactory import VectorDBProviderFactory
from src.vector_db.providers import provider_registry
from src.vector_db.providers.QdrantDBConfig import QdrantDBConfig
from src.vector_db.providers.QdrantDBProvider import QdrantDBProvider


def make_collection(name="chunks", dimension=1024):
    return VectorCollectionConfig(name=name, dimension=dimension)


def test_factory_selects_registered_builder():
    collections = [
        make_collection(name="chunks_lfm", dimension=1024),
        make_collection(name="chunks_nemotron", dimension=2048),
    ]
    provider = object()
    builder = Mock(return_value=provider)
    factory = VectorDBProviderFactory(
        builders={"fake": builder},
        default_provider="fake",
        collections=collections,
    )

    result = factory.create()

    assert result.is_success is True
    assert result.value is provider
    builder.assert_called_once()
    assert tuple(builder.call_args.args[0]) == tuple(collections)


def test_factory_explicit_provider_overrides_default():
    builder = Mock(return_value=object())
    factory = VectorDBProviderFactory(
        builders={"selected": builder},
        default_provider="default",
        collections=[make_collection()],
    )

    result = factory.create(provider="selected")

    assert result.is_success is True
    builder.assert_called_once()


def test_factory_rejects_unknown_provider():
    factory = VectorDBProviderFactory(
        builders={},
        default_provider="missing",
        collections=[make_collection()],
    )

    result = factory.create()

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_PROVIDER_UNSUPPORTED
    assert result.error.type is ErrorType.VALIDATION


def test_factory_rejects_empty_collection_configuration():
    factory = VectorDBProviderFactory(
        builders={"fake": Mock()},
        default_provider="fake",
        collections=[],
    )

    result = factory.create()

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_CONFIGURATION_INVALID


def test_factory_rejects_duplicate_collection_names():
    builder = Mock()
    factory = VectorDBProviderFactory(
        builders={"fake": builder},
        default_provider="fake",
        collections=[
            make_collection(name="chunks"),
            make_collection(name="chunks", dimension=2048),
        ],
    )

    result = factory.create()

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_CONFIGURATION_INVALID
    assert "chunks" in result.error.message
    builder.assert_not_called()


def test_factory_translates_builder_failures():
    def failing_builder(collections):
        raise RuntimeError("boom")

    factory = VectorDBProviderFactory(
        builders={"fake": failing_builder},
        default_provider="fake",
        collections=[make_collection()],
    )

    result = factory.create()

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_CONFIGURATION_INVALID


def test_qdrant_registry_converts_empty_api_key_to_none(monkeypatch):
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return object()

    class FakeQdrantDBConfig:
        @staticmethod
        def from_environment():
            return QdrantDBConfig(
                url="http://localhost:6333",
                api_key="",
                timeout=30,
            )

    monkeypatch.setattr(provider_registry, "AsyncQdrantClient", fake_client)
    monkeypatch.setattr(
        provider_registry,
        "QdrantDBConfig",
        FakeQdrantDBConfig,
    )

    provider_registry.build_qdrant_provider([make_collection()])

    assert captured["api_key"] is None


def test_qdrant_registry_builds_provider_with_one_shared_client(monkeypatch):
    client = object()
    captured = {}

    def fake_client(**kwargs):
        captured.update(kwargs)
        return client

    class FakeQdrantDBConfig:
        @staticmethod
        def from_environment():
            return QdrantDBConfig(
                url="http://qdrant:6333",
                api_key="secret",
                timeout=12,
            )

    monkeypatch.setattr(provider_registry, "AsyncQdrantClient", fake_client)
    monkeypatch.setattr(
        provider_registry,
        "QdrantDBConfig",
        FakeQdrantDBConfig,
    )
    collections = [make_collection()]

    provider = provider_registry.build_qdrant_provider(collections)

    assert isinstance(provider, QdrantDBProvider)
    assert provider._client is client
    assert captured == {
        "url": "http://qdrant:6333",
        "api_key": "secret",
        "timeout": 12,
    }
