"""Project-scoped RAG question-answering endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.business_logic.rag_business_logic import RAGBusinessLogic
from src.constants import SuccessMessage
from src.dependencies.dependency_injection import (
    get_rag_business_logic,
)
from src.dtos import (
    ApiResponse,
    RAGAnswerRequest,
    RAGAnswerResultDTO,
)


rag_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["RAG"],
)


RAGBL = Annotated[
    RAGBusinessLogic,
    Depends(get_rag_business_logic),
]


@rag_router.post(
    "/{project_id}/rag/answer",
    response_model=ApiResponse[RAGAnswerResultDTO],
)
async def answer_project_question(
    project_id: str,
    answer_request: RAGAnswerRequest,
    rag_bl: RAGBL,
) -> JSONResponse:
    result = await rag_bl.answer_question(
        project_id=project_id,
        question=answer_request.question,
    )

    return to_http_response(
        result,
        success_message=SuccessMessage.RAG_ANSWER_GENERATED,
    )
