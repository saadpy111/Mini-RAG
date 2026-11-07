"""FastAPI dependencies for vector database consumers."""

from fastapi import Request

from src.vector_db.VectorDBInterface import VectorStore


def get_vector_store(request: Request) -> VectorStore:
    """Return the lifecycle-managed vector store for business logic."""

    return request.app.state.vector_db_provider
