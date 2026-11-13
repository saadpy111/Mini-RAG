from bson import ObjectId
import pytest

from src.business_logic.rag_business_logic import RAGBusinessLogic
from src.business_logic.vector_business_logic import VectorBusinessLogic
from src.constants import ErrorCode, ErrorMessage
from src.enums import QuestionLanguage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.contracts import (
    ChatCompletionOutput,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)
from src.llm.factories import ChatProviderFactory, EmbeddingProviderFactory
from src.llm.templates import PROMPT_TEMPLATES, PromptType
from src.models.project import Project


pytestmark = pytest.mark.integration


ALPHA = "alpha chunk"
BETA = "beta chunk"
GAMMA = "gamma chunk"
ENGLISH_QUESTION = "What is alpha?"
ARABIC_QUESTION = "ما هو محتوى التقرير؟"
ARABIC_CHUNK = "التقرير يحتوي على النتائج."


class MappingEmbeddingProvider(EmbeddingProvider):
    """Deterministic embedding provider for end-to-end RAG tests."""

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


class CapturingChatProvider(ChatProvider):
    """Chat provider that records the messages sent by the RAG flow."""

    model_id = "test/chat-model"

    def __init__(self, answer="Grounded answer.", failure=None):
        self._answer = answer
        self._failure = failure
        self.messages: list[ChatMessage] = []

    async def complete(self, messages):
        self.messages = list(messages)

        if self._failure is not None:
            return Result.failure(self._failure)

        return Result.success(
            ChatCompletionOutput(
                content=self._answer,
                model=self.model_id,
            )
        )


def build_embedding_factory(provider):
    return EmbeddingProviderFactory(
        builders={"test": lambda client, model: provider},
        http_client=object(),
        default_provider="test",
        default_model="test/embedding-model",
    )


def build_chat_factory(provider):
    return ChatProviderFactory(
        builders={"test": lambda client, model: provider},
        http_client=object(),
        default_provider="test",
        default_model="test/chat-model",
    )


def build_vector_logic(
    project_repository,
    chunk_repository,
    vector_provider,
    vector_collection,
    embedding_provider,
):
    return VectorBusinessLogic(
        chunk_repository=chunk_repository,
        project_repository=project_repository,
        embedding_factory=build_embedding_factory(embedding_provider),
        vector_store=vector_provider,
        collection_name=vector_collection.name,
    )


def build_rag_logic(vector_logic, chat_provider):
    return RAGBusinessLogic(
        vector_business_logic=vector_logic,
        chat_factory=build_chat_factory(chat_provider),
    )


async def seed_project(
    project_repository,
    chunk_repository,
    make_data_chunk,
    project_id,
    texts,
):
    project = await project_repository.create(
        Project(project_id=project_id)
    )
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
    return project


def test_rag_flow_uses_project_context_and_isolates_other_projects(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    embedding_provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            BETA: [0.0, 1.0, 0.0, 0.0],
            GAMMA: [0.0, 0.0, 1.0, 0.0],
            ENGLISH_QUESTION: [1.0, 0.0, 0.0, 0.0],
        }
    )
    vector_logic = build_vector_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        embedding_provider,
    )
    chat_provider = CapturingChatProvider(
        answer="Alpha is the first chunk."
    )
    rag_logic = build_rag_logic(vector_logic, chat_provider)

    async def scenario():
        project_a = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-a",
            [ALPHA, BETA],
        )
        project_b = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-b",
            [GAMMA],
        )

        assert (
            await vector_logic.index_project(project_a.project_id)
        ).is_success is True
        assert (
            await vector_logic.index_project(project_b.project_id)
        ).is_success is True

        result = await rag_logic.answer_question(
            project_a.project_id,
            ENGLISH_QUESTION,
        )

        assert result.is_success is True
        answer = result.value
        assert answer.answer == "Alpha is the first chunk."
        assert answer.language is QuestionLanguage.ENGLISH
        assert all(
            source.project_id == project_a.project_id
            for source in answer.sources
        )
        assert {source.text for source in answer.sources} == {ALPHA, BETA}

        template = PROMPT_TEMPLATES[
            (PromptType.RAG_ANSWER, QuestionLanguage.ENGLISH)
        ]
        assert chat_provider.messages[0].content == (
            template.system_instruction
        )
        user_message = chat_provider.messages[1].content
        assert ALPHA in user_message
        assert ENGLISH_QUESTION in user_message
        assert GAMMA not in user_message

    run_async(scenario())


def test_rag_flow_selects_arabic_template(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    embedding_provider = MappingEmbeddingProvider(
        {
            ARABIC_CHUNK: [1.0, 0.0, 0.0, 0.0],
            ARABIC_QUESTION: [1.0, 0.0, 0.0, 0.0],
        }
    )
    vector_logic = build_vector_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        embedding_provider,
    )
    chat_provider = CapturingChatProvider(
        answer="يحتوي التقرير على النتائج."
    )
    rag_logic = build_rag_logic(vector_logic, chat_provider)

    async def scenario():
        project = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-arabic",
            [ARABIC_CHUNK],
        )
        index_result = await vector_logic.index_project(
            project.project_id
        )
        assert index_result.is_success is True

        result = await rag_logic.answer_question(
            project.project_id,
            ARABIC_QUESTION,
        )

        assert result.is_success is True
        assert result.value.language is QuestionLanguage.ARABIC
        assert result.value.answer == "يحتوي التقرير على النتائج."

        template = PROMPT_TEMPLATES[
            (PromptType.RAG_ANSWER, QuestionLanguage.ARABIC)
        ]
        assert chat_provider.messages[0].content == (
            template.system_instruction
        )
        user_message = chat_provider.messages[1].content
        assert ARABIC_CHUNK in user_message
        assert ARABIC_QUESTION in user_message

    run_async(scenario())


def test_rag_flow_returns_no_relevant_chunks_when_not_indexed(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    embedding_provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            ENGLISH_QUESTION: [1.0, 0.0, 0.0, 0.0],
        }
    )
    vector_logic = build_vector_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        embedding_provider,
    )
    chat_provider = CapturingChatProvider()
    rag_logic = build_rag_logic(vector_logic, chat_provider)

    async def scenario():
        project = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-unindexed",
            [ALPHA],
        )

        result = await rag_logic.answer_question(
            project.project_id,
            ENGLISH_QUESTION,
        )

        assert result.is_success is False
        assert result.error.code == ErrorCode.NO_RELEVANT_CHUNKS
        assert result.error.type is ErrorType.UNPROCESSABLE
        assert chat_provider.messages == []

    run_async(scenario())


def test_rag_flow_propagates_embedding_failure(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    embedding_provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            ENGLISH_QUESTION: [1.0, 0.0, 0.0, 0.0],
        },
        failing_texts={ENGLISH_QUESTION},
    )
    vector_logic = build_vector_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        embedding_provider,
    )
    chat_provider = CapturingChatProvider()
    rag_logic = build_rag_logic(vector_logic, chat_provider)

    async def scenario():
        project = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-embedding-failure",
            [ALPHA],
        )
        index_result = await vector_logic.index_project(
            project.project_id
        )
        assert index_result.is_success is True

        result = await rag_logic.answer_question(
            project.project_id,
            ENGLISH_QUESTION,
        )

        assert result.is_success is False
        assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR
        assert result.error.type is ErrorType.INTERNAL
        assert chat_provider.messages == []

    run_async(scenario())


def test_rag_flow_propagates_llm_failure(
    run_async,
    project_repository,
    chunk_repository,
    make_data_chunk,
    vector_provider,
    vector_collection,
):
    embedding_provider = MappingEmbeddingProvider(
        {
            ALPHA: [1.0, 0.0, 0.0, 0.0],
            ENGLISH_QUESTION: [1.0, 0.0, 0.0, 0.0],
        }
    )
    vector_logic = build_vector_logic(
        project_repository,
        chunk_repository,
        vector_provider,
        vector_collection,
        embedding_provider,
    )
    chat_provider = CapturingChatProvider(
        failure=ResultError(
            code=ErrorCode.LLM_PROVIDER_ERROR,
            message=ErrorMessage.LLM_PROVIDER_ERROR,
            type=ErrorType.INTERNAL,
        )
    )
    rag_logic = build_rag_logic(vector_logic, chat_provider)

    async def scenario():
        project = await seed_project(
            project_repository,
            chunk_repository,
            make_data_chunk,
            "project-llm-failure",
            [ALPHA],
        )
        index_result = await vector_logic.index_project(
            project.project_id
        )
        assert index_result.is_success is True

        result = await rag_logic.answer_question(
            project.project_id,
            ENGLISH_QUESTION,
        )

        assert result.is_success is False
        assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR
        assert chat_provider.messages

    run_async(scenario())
