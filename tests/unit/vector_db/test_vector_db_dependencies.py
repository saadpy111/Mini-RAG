from types import SimpleNamespace

from src.vector_db.VectorDBDependencies import get_vector_store


def test_get_vector_store_returns_lifecycle_managed_provider():
    provider = object()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(vector_db_provider=provider),
        )
    )

    assert get_vector_store(request) is provider
