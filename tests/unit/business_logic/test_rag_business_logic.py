import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.business_logic.rag_business_logic import (
    DEFAULT_CONTEXT_LIMIT,
    RAGBusinessLogic,
)
from src.business_logic.vector_business_logic import VectorBusinessLogic
from src.constants import ErrorCode, ErrorMessage
from src.enums import QuestionLanguage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.contracts import ChatCompletionOutput, ChatProvider
from src.llm.factories import ChatProviderFactory
from src.llm.templates import PROMPT_TEMPLATES, PromptType
from src.vector_db.VectorDBModels import VectorSearchResult


def make_error(
    code=ErrorCode.LLM_PROVIDER_ERROR,
    error_type=ErrorType.INTERNAL,
):
    return ResultError(
        code=code,
        message=ErrorMessage.LLM_PROVIDER_ERROR,
        type=error_type,
    )


def make_result(
    text="Alpha chunk.",
    chunk_id="chunk-1",
    score=0.9,
):
    return VectorSearchResult(
        vector_id=f"vector-{chunk_id}",
        score=score,
        metadata={
            "project_id": "project-1",
            "asset_id": "asset-1",
            "chunk_id": chunk_id,
            "chunk_index": 1,
            "text": text,
        },
    )


@pytest.fixture
def vector_business_logic():
    return AsyncMock(spec=VectorBusinessLogic)


@pytest.fixture
def chat_provider():
    provider = AsyncMock(spec=ChatProvider)
    provider.model_id = "test/chat-model"
    return provider


@pytest.fixture
def chat_factory(chat_provider):
    factory = Mock(spec=ChatProviderFactory)
    factory.create.return_value = Result.success(chat_provider)
    return factory


@pytest.fixture
def logic(vector_business_logic, chat_factory):
    return RAGBusinessLogic(
        vector_business_logic=vector_business_logic,
        chat_factory=chat_factory,
    )


def test_english_question_uses_english_template_and_retrieved_context(
    logic,
    vector_business_logic,
    chat_provider,
    chat_factory,
):
    vector_business_logic.search_project.return_value = Result.success(
        [make_result("Alpha chunk.")]
    )
    chat_provider.complete.return_value = Result.success(
        ChatCompletionOutput(
            content="Alpha is the first chunk.",
            model="test/chat-model",
        )
    )

    result = asyncio.run(
        logic.answer_question("project-1", "  What is Alpha?  ")
    )

    assert result.is_success is True
    answer = result.value
    assert answer.project_id == "project-1"
    assert answer.question == "What is Alpha?"
    assert answer.answer == "Alpha is the first chunk."
    assert answer.language is QuestionLanguage.ENGLISH
    assert answer.model == "test/chat-model"
    assert [source.chunk_id for source in answer.sources] == ["chunk-1"]

    vector_business_logic.search_project.assert_awaited_once_with(
        project_id="project-1",
        query="What is Alpha?",
        limit=DEFAULT_CONTEXT_LIMIT,
    )
    chat_factory.create.assert_called_once_with()

    messages = chat_provider.complete.await_args.args[0]
    template = PROMPT_TEMPLATES[
        (PromptType.RAG_ANSWER, QuestionLanguage.ENGLISH)
    ]
    assert messages[0].content == template.system_instruction
    assert "Alpha chunk." in messages[1].content
    assert "What is Alpha?" in messages[1].content


def test_arabic_question_uses_arabic_template_and_retrieved_context(
    logic,
    vector_business_logic,
    chat_provider,
):
    arabic_chunk = "التقرير يحتوي على النتائج."
    vector_business_logic.search_project.return_value = Result.success(
        [make_result(arabic_chunk)]
    )
    chat_provider.complete.return_value = Result.success(
        ChatCompletionOutput(
            content="يحتوي التقرير على النتائج.",
            model="test/chat-model",
        )
    )

    result = asyncio.run(
        logic.answer_question("project-1", "ما هو محتوى التقرير؟")
    )

    assert result.is_success is True
    answer = result.value
    assert answer.language is QuestionLanguage.ARABIC
    assert answer.answer == "يحتوي التقرير على النتائج."

    messages = chat_provider.complete.await_args.args[0]
    template = PROMPT_TEMPLATES[
        (PromptType.RAG_ANSWER, QuestionLanguage.ARABIC)
    ]
    assert messages[0].content == template.system_instruction
    assert arabic_chunk in messages[1].content
    assert "ما هو محتوى التقرير؟" in messages[1].content


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_empty_question_fails_before_retrieval(
    logic,
    vector_business_logic,
    chat_factory,
    question,
):
    result = asyncio.run(
        logic.answer_question("project-1", question)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.EMPTY_RAG_QUESTION
    assert result.error.type is ErrorType.VALIDATION
    vector_business_logic.search_project.assert_not_awaited()
    chat_factory.create.assert_not_called()


@pytest.mark.parametrize("project_id", ["", "   ", "\n"])
def test_empty_project_id_fails_before_retrieval(
    logic,
    vector_business_logic,
    chat_factory,
    project_id,
):
    result = asyncio.run(
        logic.answer_question(project_id, "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.INVALID_PROJECT_ID
    assert result.error.type is ErrorType.VALIDATION
    vector_business_logic.search_project.assert_not_awaited()
    chat_factory.create.assert_not_called()


def test_no_retrieval_results_returns_no_relevant_chunks(
    logic,
    vector_business_logic,
    chat_factory,
):
    vector_business_logic.search_project.return_value = Result.success([])

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.NO_RELEVANT_CHUNKS
    assert result.error.type is ErrorType.UNPROCESSABLE
    chat_factory.create.assert_not_called()


def test_blank_retrieval_results_return_no_relevant_chunks(
    logic,
    vector_business_logic,
    chat_factory,
):
    vector_business_logic.search_project.return_value = Result.success(
        [make_result("   ")]
    )

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.NO_RELEVANT_CHUNKS
    chat_factory.create.assert_not_called()


def test_propagates_retrieval_failure(
    logic,
    vector_business_logic,
    chat_factory,
):
    error = make_error(ErrorCode.VECTOR_DB_SEARCH_FAILED)
    vector_business_logic.search_project.return_value = Result.failure(
        error
    )

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error is error
    chat_factory.create.assert_not_called()


def test_propagates_chat_factory_failure(
    logic,
    vector_business_logic,
    chat_provider,
    chat_factory,
):
    error = make_error(ErrorCode.LLM_PROVIDER_UNSUPPORTED)
    vector_business_logic.search_project.return_value = Result.success(
        [make_result()]
    )
    chat_factory.create.return_value = Result.failure(error)

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error is error
    chat_provider.complete.assert_not_awaited()


def test_propagates_llm_completion_failure(
    logic,
    vector_business_logic,
    chat_provider,
):
    error = make_error(ErrorCode.LLM_PROVIDER_ERROR)
    vector_business_logic.search_project.return_value = Result.success(
        [make_result()]
    )
    chat_provider.complete.return_value = Result.failure(error)

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is False
    assert result.error is error


def test_duplicate_chunks_are_sent_to_the_model_only_once(
    logic,
    vector_business_logic,
    chat_provider,
):
    vector_business_logic.search_project.return_value = Result.success(
        [
            make_result("Alpha chunk.", chunk_id="chunk-1"),
            make_result("Alpha chunk.", chunk_id="chunk-1"),
        ]
    )
    chat_provider.complete.return_value = Result.success(
        ChatCompletionOutput(
            content="Grounded answer.",
            model="test/chat-model",
        )
    )

    result = asyncio.run(
        logic.answer_question("project-1", "What is Alpha?")
    )

    assert result.is_success is True
    assert len(result.value.sources) == 1

    messages = chat_provider.complete.await_args.args[0]
    assert messages[1].content.count("Alpha chunk.") == 1
