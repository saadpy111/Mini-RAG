from bson import ObjectId
import pytest

from src.business_logic.vector_business_logic import (
    VectorBusinessLogic,
    chunk_vector_id,
)
from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.contracts import EmbeddingProvider
from src.llm.factories import EmbeddingProviderFactory
from src.models.project import Project

pytestmark = pytest.mark.integration


ALPHA = "alpha chunk"
BETA = "beta chunk"
GAMMA = "gamma chunk"


class MappingEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider for end-to-end vector tests."""

    model_id = "test/embedding-model"

    def __init__(self, vectors, failing_texts=()):
        self._vectors = vectors
        self._failing_texts = set(failing_texts)

    async def embed(self, text):
        if text in self._failing_texts:
            return Result.failure(
                ResultError(
                    code=ErrorCode.LLM_PROVIDER_ERROR,
                    message=ErrorMessage.LLM_PROVIDER_ERROR,
                    type=ErrorType.INTERNAL,
                )
            )

        return Result.success(list(self._vectors[text]))


def build_embedding_factory(provider):
    return EmbeddingProviderFactory(
        builders={"test": lambda client, model: provider},
        http_client=object(),
        default_provider="test",
        default_model="test/embedding-model",
    )


def build_logic(
    project_repository,
    chunk_repository,
    vector_provider,
    vector_collection,
    provider,
):
    return VectorBusinessLogic(
        chunk_repository=chunk_repository,
        project_repository=project_repository,
        embedding_factory=build_embedding_factory(provider),
        vector_store=vector_provider,
        collection_name=vector_collection.name,
    )


async def seed_project(
    project_repository,
    chunk_repository,
    make_data_chunk,
    project_id,
    texts,
):
    project = await project_repository.create(Project(project_id=project_id))
    asset_id = ObjectId()
    chunks = [
        make_data_chunk(
            project.id,
            asset_id,
            text=text,
            order=index,
        )
        for index, text in enumerate(texts, start=1)
    ]
    await chunk_repository.insert_many_chunks(chunks)
    stored = await chunk_repository.get_all_by_project_id(project.id)
    return project, stored


def by_text(chunks):
    return {chunk.chunk_text: chunk for chunk in chunks}


def test_full_flow_indexes_chunks_and_searches_within_project(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            BETA: [0.0, 1.0, 0.0, 0.0],
            GAMMA: [0.0, 0.0, 1.0, 0.0],
        }
    )
    logic = build_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        provider,
    )

    async def scenario():
        project_a, chunks_a = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-a",
            [ALPHA, BETA, GAMMA],
        )
        project_b, _ = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-b",
            [ALPHA],
        )

        assert (
            await logic.index_project(project_a.project_id)
        ).value == 3
        assert (
            await logic.index_project(project_b.project_id)
        ).value == 1

        search_result = await logic.search_project(
            project_a.project_id,
            ALPHA,
            limit=5,
        )

        assert search_result.is_success is True
        results = search_result.value
        assert len(results) == 3
        assert results[0].metadata["text"] == ALPHA
        assert results[0].score == pytest.approx(1.0, abs=1e-6)
        assert all(
            item.metadata["project_id"] == project_a.project_id
            for item in results
        )

        alpha_chunk = by_text(chunks_a)[ALPHA]
        assert results[0].vector_id == chunk_vector_id(alpha_chunk.id)
        assert results[0].metadata == {
            "project_id": project_a.project_id,
            "asset_id": str(alpha_chunk.chunk_asset_id),
            "chunk_id": str(alpha_chunk.id),
            "chunk_index": alpha_chunk.chunk_order,
            "text": ALPHA,
        }

        limited_result = await logic.search_project(
            project_a.project_id,
            ALPHA,
            limit=1,
        )
        assert len(limited_result.value) == 1

        project_b_result = await logic.search_project(
            project_b.project_id,
            ALPHA,
            limit=5,
        )
        assert len(project_b_result.value) == 1
        assert all(
            item.metadata["project_id"] == project_b.project_id
            for item in project_b_result.value
        )

    run_async(scenario())


def test_search_returns_empty_results_when_project_is_not_indexed(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    provider = MappingEmbeddingProvider({ALPHA: [1.0, 0.0, 0.0, 0.0]})
    logic = build_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        provider,
    )

    async def scenario():
        project, _ = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-unindexed",
            [ALPHA],
        )

        result = await logic.search_project(project.project_id, ALPHA)

        assert result.is_success is True
        assert result.value == []

    run_async(scenario())


def test_reset_removes_stale_vectors_while_regular_reindex_keeps_them(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            BETA: [0.0, 1.0, 0.0, 0.0],
        }
    )
    logic = build_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        provider,
    )

    async def stored_ids(project):
        result = await vector_provider.list_ids_by_project(
            vector_collection.name,
            project.project_id,
        )
        assert result.is_success is True
        return set(result.value)

    async def scenario():
        project, chunks = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-reset",
            [ALPHA, BETA],
        )
        await logic.index_project(project.project_id)

        alpha_chunk = by_text(chunks)[ALPHA]
        beta_chunk = by_text(chunks)[BETA]
        assert await stored_ids(project) == {
            chunk_vector_id(alpha_chunk.id),
            chunk_vector_id(beta_chunk.id),
        }

        await chunk_repository.delete_by_ids([beta_chunk.id])

        reindex_result = await logic.index_project(project.project_id)
        assert reindex_result.is_success is True
        assert reindex_result.value == 1
        assert await stored_ids(project) == {
            chunk_vector_id(alpha_chunk.id),
            chunk_vector_id(beta_chunk.id),
        }

        reset_result = await logic.index_project(
            project.project_id,
            do_reset=True,
        )
        assert reset_result.is_success is True
        assert reset_result.value == 1
        assert await stored_ids(project) == {
            chunk_vector_id(alpha_chunk.id),
        }

    run_async(scenario())


def test_failed_reindex_preserves_existing_vectors(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    vectors = {
        ALPHA: [1.0, 0.0, 0.0, 0.0],
        BETA: [0.0, 1.0, 0.0, 0.0],
        GAMMA: [0.0, 0.0, 1.0, 0.0],
    }
    working_logic = build_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        MappingEmbeddingProvider(vectors),
    )
    failing_logic = build_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        MappingEmbeddingProvider(vectors, failing_texts={GAMMA}),
    )

    async def scenario():
        project, chunks = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-failure",
            [ALPHA, BETA],
        )
        assert (
            await working_logic.index_project(project.project_id)
        ).value == 2

        initial_ids = {
            chunk_vector_id(chunk.id) for chunk in chunks
        }
        stored = await vector_provider.list_ids_by_project(
            vector_collection.name,
            project.project_id,
        )
        assert set(stored.value) == initial_ids

        await chunk_repository.create_chunk(
            make_data_chunk(
                project.id,
                chunks[0].chunk_asset_id,
                text=GAMMA,
                order=3,
            )
        )

        result = await failing_logic.index_project(
            project.project_id,
            do_reset=True,
        )

        assert result.is_success is False
        assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR

        stored_after = await vector_provider.list_ids_by_project(
            vector_collection.name,
            project.project_id,
        )
        assert set(stored_after.value) == initial_ids

        search_result = await working_logic.search_project(
            project.project_id,
            BETA,
            limit=1,
        )
        assert search_result.is_success is True
        assert search_result.value[0].metadata["text"] == BETA

    run_async(scenario())
