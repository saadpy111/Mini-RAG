"""Build grounded LLM context from retrieved vector search results."""

from collections.abc import Sequence
from dataclasses import dataclass

from src.constants import ErrorCode, ErrorMessage
from src.dtos.responses.vector_result import VectorSearchResultDTO
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.vector_db.VectorDBModels import VectorSearchResult


@dataclass(frozen=True, slots=True)
class GroundedContext:
    """Usable context text and the chunks it was built from."""

    text: str
    sources: list[VectorSearchResultDTO]


def build_grounded_context(
    results: Sequence[VectorSearchResult],
) -> Result[GroundedContext]:
    """Format retrieved chunks into a numbered, deduplicated context."""

    blocks: list[str] = []
    sources: list[VectorSearchResultDTO] = []
    seen_chunk_ids: set[str] = set()

    for result in results:
        metadata = result.metadata
        text = str(metadata.get("text") or "").strip()

        if not text:
            continue

        chunk_id = str(metadata.get("chunk_id") or result.vector_id)

        if chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk_id)
        blocks.append(f"[{len(blocks) + 1}] {text}")
        sources.append(VectorSearchResultDTO.from_search_result(result))

    if not blocks:
        return Result.failure(
            ResultError(
                code=ErrorCode.NO_RELEVANT_CHUNKS,
                message=ErrorMessage.NO_RELEVANT_CHUNKS,
                type=ErrorType.UNPROCESSABLE,
            )
        )

    return Result.success(
        GroundedContext(
            text="\n\n".join(blocks),
            sources=sources,
        )
    )
