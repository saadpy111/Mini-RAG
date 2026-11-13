from src.constants import ErrorCode
from src.helpers.result_pattern import ErrorType
from src.services.rag_context_service import build_grounded_context
from src.vector_db.VectorDBModels import VectorSearchResult


def make_result(
    text,
    chunk_id="chunk-1",
    vector_id="vector-1",
    score=0.9,
    project_id="project-1",
    asset_id="asset-1",
    chunk_index=1,
):
    return VectorSearchResult(
        vector_id=vector_id,
        score=score,
        metadata={
            "text": text,
            "chunk_id": chunk_id,
            "project_id": project_id,
            "asset_id": asset_id,
            "chunk_index": chunk_index,
        },
    )


def test_builds_numbered_context_and_sources():
    results = [
        make_result("first chunk", chunk_id="chunk-1"),
        make_result("second chunk", chunk_id="chunk-2"),
    ]

    result = build_grounded_context(results)

    assert result.is_success is True
    assert result.value.text == "[1] first chunk\n\n[2] second chunk"
    assert [source.chunk_id for source in result.value.sources] == [
        "chunk-1",
        "chunk-2",
    ]
    assert result.value.sources[0].text == "first chunk"
    assert result.value.sources[0].score == 0.9


def test_skips_blank_and_duplicate_chunks():
    results = [
        make_result("first chunk", chunk_id="chunk-1"),
        make_result("   ", chunk_id="chunk-2"),
        make_result("duplicate chunk", chunk_id="chunk-1"),
    ]

    result = build_grounded_context(results)

    assert result.is_success is True
    assert result.value.text == "[1] first chunk"
    assert len(result.value.sources) == 1
    assert result.value.sources[0].chunk_id == "chunk-1"


def test_returns_no_relevant_chunks_when_no_usable_text():
    results = [
        make_result("", chunk_id="chunk-1"),
        make_result("   ", chunk_id="chunk-2"),
    ]

    result = build_grounded_context(results)

    assert result.is_success is False
    assert result.error.code == ErrorCode.NO_RELEVANT_CHUNKS
    assert result.error.type is ErrorType.UNPROCESSABLE


def test_returns_no_relevant_chunks_for_empty_results():
    result = build_grounded_context([])

    assert result.is_success is False
    assert result.error.code == ErrorCode.NO_RELEVANT_CHUNKS
    assert result.error.type is ErrorType.UNPROCESSABLE
