import pytest

from src.constants import ErrorCode, ErrorMessage, SuccessMessage
from src.dependencies.dependency_injection import get_rag_business_logic
from src.dtos import RAGAnswerResultDTO
from src.dtos.responses.vector_result import VectorSearchResultDTO
from src.enums import QuestionLanguage
from src.helpers.result_pattern import ErrorType, Result, ResultError


def rag_answer_url(project_id):
    return f"/api/v1/projects/{project_id}/rag/answer"


def make_answer(
    project_id="project-1",
    question="What is RAG?",
    answer="RAG combines retrieval with generation.",
    language=QuestionLanguage.ENGLISH,
):
    return RAGAnswerResultDTO(
        project_id=project_id,
        question=question,
        answer=answer,
        language=language,
        model="test/chat-model",
        sources=[
            VectorSearchResultDTO(
                chunk_id="chunk-1",
                project_id=project_id,
                asset_id="asset-1",
                chunk_index=1,
                text="RAG combines retrieval with generation.",
                score=0.9,
            )
        ],
    )


@pytest.fixture
def rag_context(override_business_logic, rag_bl):
    override_business_logic(get_rag_business_logic, rag_bl)
    return rag_bl


def test_answer_success_returns_standard_envelope(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.success(
        make_answer()
    )

    response = client.post(
        rag_answer_url("project-1"),
        json={"question": "What is RAG?"},
    )

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=200,
        message=SuccessMessage.RAG_ANSWER_GENERATED,
    )

    data = body["data"]
    assert data["project_id"] == "project-1"
    assert data["question"] == "What is RAG?"
    assert data["answer"] == "RAG combines retrieval with generation."
    assert data["language"] == "en"
    assert data["model"] == "test/chat-model"
    assert data["sources"][0]["chunk_id"] == "chunk-1"
    assert data["sources"][0]["text"] == (
        "RAG combines retrieval with generation."
    )

    rag_context.answer_question.assert_awaited_once_with(
        project_id="project-1",
        question="What is RAG?",
    )


def test_answer_success_in_arabic(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.success(
        make_answer(
            question="ما هو RAG؟",
            answer="يجمع RAG بين الاسترجاع والتوليد.",
            language=QuestionLanguage.ARABIC,
        )
    )

    response = client.post(
        rag_answer_url("project-1"),
        json={"question": "ما هو RAG؟"},
    )

    body = assert_api_envelope(response, is_success=True, status_code=200)

    assert body["data"]["language"] == "ar"
    assert body["data"]["answer"] == "يجمع RAG بين الاسترجاع والتوليد."


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 4001},
    ],
)
def test_rejects_invalid_question_before_business_logic(
    client,
    rag_context,
    assert_api_envelope,
    payload,
):
    response = client.post(
        rag_answer_url("project-1"),
        json=payload,
    )

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.REQUEST_VALIDATION_FAILED
    rag_context.answer_question.assert_not_awaited()


def test_returns_project_not_found(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.failure(
        ResultError(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=ErrorMessage.PROJECT_WAS_NOT_FOUND,
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(
        rag_answer_url("missing-project"),
        json={"question": "What is RAG?"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == ErrorMessage.PROJECT_WAS_NOT_FOUND


def test_returns_no_relevant_chunks(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.failure(
        ResultError(
            code=ErrorCode.NO_RELEVANT_CHUNKS,
            message=ErrorMessage.NO_RELEVANT_CHUNKS,
            type=ErrorType.UNPROCESSABLE,
        )
    )

    response = client.post(
        rag_answer_url("project-1"),
        json={"question": "What is RAG?"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.NO_RELEVANT_CHUNKS


def test_returns_llm_failure(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.failure(
        ResultError(
            code=ErrorCode.LLM_PROVIDER_ERROR,
            message=ErrorMessage.LLM_PROVIDER_ERROR,
            type=ErrorType.INTERNAL,
        )
    )

    response = client.post(
        rag_answer_url("project-1"),
        json={"question": "What is RAG?"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.LLM_PROVIDER_ERROR


def test_returns_service_unavailable_for_rate_limited_llm(
    client,
    rag_context,
    assert_api_envelope,
):
    rag_context.answer_question.return_value = Result.failure(
        ResultError(
            code=ErrorCode.LLM_RATE_LIMITED,
            message=ErrorMessage.LLM_RATE_LIMITED,
            type=ErrorType.SERVICE_UNAVAILABLE,
        )
    )

    response = client.post(
        rag_answer_url("project-1"),
        json={"question": "What is RAG?"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=503)

    assert body["message"] == ErrorMessage.LLM_RATE_LIMITED
