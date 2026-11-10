"""Vector indexing and semantic search endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.business_logic.vector_business_logic import VectorBusinessLogic
from src.constants import SuccessMessage
from src.dependencies.dependency_injection import (
    get_vector_business_logic,
)
from src.dtos import (
    ApiResponse,
    VectorIndexRequest,
    VectorIndexResultDTO,
    VectorSearchRequest,
    VectorSearchResultDTO,
)
from src.helpers.result_pattern import Result
from src.vector_db.VectorDBModels import VectorSearchResult


vector_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Vectors"],
)


VectorBL = Annotated[
    VectorBusinessLogic,
    Depends(get_vector_business_logic),
]


def _to_search_result_dto(
    result: VectorSearchResult,
) -> VectorSearchResultDTO:
    metadata = result.metadata

    return VectorSearchResultDTO(
        chunk_id=str(metadata.get("chunk_id", result.vector_id)),
        project_id=str(metadata.get("project_id", "")),
        asset_id=str(metadata.get("asset_id", "")),
        chunk_index=int(metadata.get("chunk_index", 0) or 0),
        text=str(metadata.get("text", "")),
        score=result.score,
    )


@vector_router.post(
    "/{project_id}/vectors/index",
    response_model=ApiResponse[VectorIndexResultDTO],
)
async def index_project_vectors(
    project_id: str,
    vector_bl: VectorBL,
    vector_request: VectorIndexRequest | None = None,
) -> JSONResponse:
    options = vector_request or VectorIndexRequest()

    result = await vector_bl.index_project(
        project_id=project_id,
        do_reset=options.do_reset,
    )

    if not result.is_success:
        return to_http_response(result)

    response = VectorIndexResultDTO(
        project_id=project_id,
        indexed_count=result.value or 0,
    )

    return to_http_response(
        Result.success(response),
        success_message=SuccessMessage.VECTORS_INDEXED,
    )


@vector_router.post(
    "/{project_id}/vectors/search",
    response_model=ApiResponse[list[VectorSearchResultDTO]],
)
async def search_project_vectors(
    project_id: str,
    search_request: VectorSearchRequest,
    vector_bl: VectorBL,
) -> JSONResponse:
    result = await vector_bl.search_project(
        project_id=project_id,
        query=search_request.query,
        limit=search_request.limit,
    )

    if not result.is_success:
        return to_http_response(result)

    search_results = [
        _to_search_result_dto(item)
        for item in (result.value or [])
    ]

    return to_http_response(
        Result.success(search_results),
        success_message=SuccessMessage.VECTOR_SEARCH_COMPLETED,
    )
